import XCTest

/// The tutor chat against the real API with a fake AI (web/e2e/server.py, port 8797): it
/// answers by keywords — "công thức dài" (a very wide formula), "lỗi ai" (an AI failure),
/// "đáp án mới", else a hint that moves the level to 2.
@MainActor
final class ChatTests: XCTestCase {
    private var app: XCUIApplication!

    override func setUp() async throws {
        continueAfterFailure = false
        app = XCUIApplication()
        let api = ProcessInfo.processInfo.environment["MATHMATE_TEST_API"] ?? "http://127.0.0.1:8797"
        app.launchArguments = ["-uiTesting", "-api", api]
        app.launch()
        XCTAssertTrue(app.buttons["tryAsGuest"].waitForExistence(timeout: 10))
        app.buttons["tryAsGuest"].tap()
        XCTAssertTrue(app.buttons["newConversation"].waitForExistence(timeout: 10))
        // iPhone: the list comes first; a new conversation opens the chat.
        app.buttons["newConversation"].tap()
    }

    /// A multi-line TextField: a text field on iOS 26, a text view on iOS 17.
    private func field(_ identifier: String) -> XCUIElement {
        let textField = app.textFields[identifier]
        _ = app.descendants(matching: .any)[identifier].firstMatch.waitForExistence(timeout: 10)
        return textField.exists ? textField : app.textViews[identifier]
    }

    private var composer: XCUIElement { field("composer") }

    private func send(_ text: String) {
        XCTAssertTrue(composer.waitForExistence(timeout: 10))
        composer.tap()
        composer.typeText(text)
        app.buttons["send"].tap()
    }

    private func text(containing fragment: String) -> XCUIElement {
        app.staticTexts.containing(NSPredicate(format: "label CONTAINS %@", fragment)).firstMatch
    }

    private func waitForText(_ fragment: String, timeout: TimeInterval = 20) -> Bool {
        let predicate = NSPredicate(format: "label CONTAINS %@", fragment)
        return app.staticTexts.matching(predicate).firstMatch.waitForExistence(timeout: timeout)
    }

    func testTheTutorAnswersAndGoesDeeper() {
        send("Giải phương trình x + 1 = 3")
        XCTAssertTrue(waitForText("Mình cùng đọc kỹ đề nhé"), "the reply arrives")
        XCTAssertFalse(waitForText("[[bac", timeout: 1), "the progress tag never shows")
        XCTAssertTrue(waitForText("Nhớ kiến thức"), "the tutor moved to level 2")

        let deeper = app.buttons["deeperHint"]
        XCTAssertTrue(deeper.waitForExistence(timeout: 10))
        let before = app.descendants(matching: .any).matching(identifier: "assistantMessage").count
        deeper.tap()
        let more = NSPredicate(format: "count > %d", before)
        let replies = app.descendants(matching: .any).matching(identifier: "assistantMessage")
        XCTAssertEqual(XCTWaiter.wait(for: [expectation(for: more, evaluatedWith: replies)], timeout: 20), .completed)
    }

    func testTheLastMessageCanBeEdited() {
        send("Giải phương trình x + 1 = 3")
        XCTAssertTrue(waitForText("Mình cùng đọc kỹ đề nhé"))
        let message = app.descendants(matching: .any).matching(identifier: "userMessage").firstMatch
        message.press(forDuration: 1.0)
        app.buttons["Sửa tin nhắn"].tap()
        let edit = field("editText")
        XCTAssertTrue(edit.exists)
        // The sheet opens with the keyboard on the message.
        let focused = NSPredicate(format: "hasKeyboardFocus == true")
        XCTAssertEqual(XCTWaiter.wait(for: [expectation(for: focused, evaluatedWith: edit)], timeout: 5), .completed)
        edit.typeText(" — đáp án mới")
        app.buttons["saveEdit"].tap()
        XCTAssertTrue(waitForText("Mình đã xem đáp án mới của em"))
        XCTAssertTrue(waitForText("đáp án mới"))
    }

    func testAVeryWideFormulaStillShows() {
        send("Cho em hỏi công thức dài")
        XCTAssertTrue(waitForText("Biểu thức rất dài"))
        XCTAssertTrue(waitForText("Em thấy gì?"))
    }

    func testAnAIFailureIsSavedAsAnErrorMessage() {
        send("Thử lỗi ai nhé")
        let replies = app.descendants(matching: .any).matching(identifier: "assistantMessage")
        XCTAssertTrue(replies.firstMatch.waitForExistence(timeout: 20), "an error reply is shown")
        XCTAssertTrue(composer.isHittable, "the chat stays usable")
    }
}
