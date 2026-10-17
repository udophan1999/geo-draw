import XCTest

/// Sign up, try as a guest, settings and account deletion against a real API with a fake AI:
/// `.venv/bin/python web/e2e/server.py 8797` from the repo root (a temporary data folder).
@MainActor
final class AccountTests: XCTestCase {
    private var app: XCUIApplication!

    override func setUp() async throws {
        continueAfterFailure = false
        app = XCUIApplication()
        let api = ProcessInfo.processInfo.environment["MATHMATE_TEST_API"] ?? "http://127.0.0.1:8797"
        app.launchArguments = ["-uiTesting", "-api", api]
        app.launch()
    }

    /// Types into the text field itself (a `descendants(matching: .any)` query can land on a
    /// container, and XCUITest then taps again for every keystroke).
    private func type(_ identifier: String, _ text: String) {
        XCTAssertTrue(app.descendants(matching: .any)[identifier].firstMatch.waitForExistence(timeout: 5),
                      "missing \(identifier)")
        let secure = app.secureTextFields[identifier]
        let field = secure.exists ? secure : app.textFields[identifier]
        // A field just above the keyboard sits under its suggestion bar: scroll it up first.
        let keyboard = app.keyboards.firstMatch
        if keyboard.exists, field.frame.maxY > keyboard.frame.minY - 60 {
            app.scrollViews.firstMatch.swipeUp()
        }
        field.tap()
        field.typeText(text)
    }

    /// Scrolls a form until the element can be tapped (a Form builds its rows only as they come
    /// on screen, so the element may not exist yet).
    private func tapAfterScrolling(_ element: XCUIElement) {
        XCTAssertTrue(app.collectionViews.firstMatch.waitForExistence(timeout: 5))
        for _ in 0..<6 where !(element.exists && element.isHittable) {
            app.collectionViews.firstMatch.swipeUp()
        }
        element.tap()
    }

    private var uniqueName: String { "ios\(Int(Date().timeIntervalSince1970 * 1000) % 100_000_000)" }

    func testGuestCanTryWithoutAnAccount() {
        XCTAssertTrue(app.staticTexts["Đăng nhập"].waitForExistence(timeout: 10))
        app.buttons["tryAsGuest"].tap()
        XCTAssertTrue(app.staticTexts["Đăng nhập để lưu lại lịch sử hỏi đáp"].waitForExistence(timeout: 10))
    }

    /// A password typed right after the username must keep every character.
    func testPasswordKeepsEveryCharacterAfterTheUsername() {
        type("username", "hocsinh")
        type("password", "abcdef")
        XCTAssertEqual(app.secureTextFields["password"].value as? String, "••••••")
        app.buttons["showRegister"].tap()
        type("username", "hocsinh")
        type("password", "abcdef")
        type("confirmPassword", "abcdef")
        XCTAssertEqual(app.secureTextFields["password"].value as? String, "••••••")
        XCTAssertEqual(app.secureTextFields["confirmPassword"].value as? String, "••••••")
    }

    func testWrongPasswordIsRefused() {
        type("username", "khong-ton-tai")
        type("password", "sai-mat-khau")
        app.buttons["loginButton"].tap()
        XCTAssertTrue(app.staticTexts["Sai tên đăng nhập hoặc mật khẩu."].waitForExistence(timeout: 10))
    }

    func testRegisterChecksPasswordsThenSignsIn() {
        app.buttons["showRegister"].tap()
        let name = uniqueName
        type("username", name)
        type("password", "123")
        type("confirmPassword", "123")
        app.buttons["registerButton"].tap()
        XCTAssertEqual(app.staticTexts["authError"].label, "Mật khẩu phải có ít nhất 6 ký tự.")

        app.secureTextFields["password"].tap()
        app.secureTextFields["password"].typeText("456789")  // now "123456789"
        app.buttons["registerButton"].tap()
        XCTAssertEqual(app.staticTexts["authError"].label, "Hai lần nhập mật khẩu không khớp.")
        app.secureTextFields["confirmPassword"].tap()
        app.secureTextFields["confirmPassword"].typeText("456789")
        app.buttons["registerButton"].tap()
        XCTAssertTrue(app.staticTexts["Chào \(name)!"].waitForExistence(timeout: 10)
                      || app.buttons["newConversation"].waitForExistence(timeout: 5))
    }

    func testTakenNameOffersSuggestionsAndDeletingTheAccountFreesIt() throws {
        let name = uniqueName
        // Create the account, then sign out.
        app.buttons["showRegister"].tap()
        type("username", name)
        type("password", "matkhau123")
        type("confirmPassword", "matkhau123")
        app.buttons["registerButton"].tap()
        XCTAssertTrue(app.buttons["accountMenu"].waitForExistence(timeout: 10))
        app.buttons["accountMenu"].tap()
        app.buttons["Đăng xuất"].tap()

        // The same name again: refused with suggestions that fill the field.
        XCTAssertTrue(app.buttons["showRegister"].waitForExistence(timeout: 10))
        app.buttons["showRegister"].tap()
        type("username", name)
        type("password", "matkhau123")
        type("confirmPassword", "matkhau123")
        app.buttons["registerButton"].tap()
        let suggestion = app.buttons["\(name) 2"]
        XCTAssertTrue(suggestion.waitForExistence(timeout: 10))

        // Sign in with the first account and delete it from the settings.
        app.buttons["showLogin"].tap()
        type("username", name)
        type("password", "matkhau123")
        app.buttons["loginButton"].tap()
        XCTAssertTrue(app.buttons["accountMenu"].waitForExistence(timeout: 10))
        app.buttons["accountMenu"].tap()
        app.buttons["Cài đặt"].tap()
        tapAfterScrolling(app.buttons["deleteAccount"])
        type("deletePassword", "sai-mat-khau")
        app.buttons["confirmDelete"].tap()
        XCTAssertTrue(app.staticTexts["Mật khẩu không đúng."].waitForExistence(timeout: 10))
        type("deletePassword", "matkhau123")  // a wrong password empties the field
        app.buttons["confirmDelete"].tap()
        XCTAssertTrue(app.buttons["loginButton"].waitForExistence(timeout: 10))

        // The account is gone.
        type("username", name)
        type("password", "matkhau123")
        app.buttons["loginButton"].tap()
        XCTAssertTrue(app.staticTexts["Sai tên đăng nhập hoặc mật khẩu."].waitForExistence(timeout: 10))
    }
}
