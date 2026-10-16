import XCTest

/// The message box's formula rules (as web/e2e/composer.spec.ts checks them on the web).
/// The box reports the message it would send (`$latex$` for chips) as its value.
@MainActor
final class ComposerTests: XCTestCase {
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
        app.buttons["newConversation"].tap()
        XCTAssertTrue(composer.waitForExistence(timeout: 10))
    }

    private var composer: XCUIElement { app.textViews["composer"] }
    private var message: String { composer.value as? String ?? "" }

    private func type(_ text: String) {
        if (composer.value(forKey: "hasKeyboardFocus") as? Bool) != true { composer.tap() }
        composer.typeText(text)
    }

    private func backspace() { composer.typeText(XCUIKeyboardKey.delete.rawValue) }

    func testATypedFormulaBecomesAChipAndBackspaceGivesItBack() {
        type("a $x^2$")
        XCTAssertEqual(message, "a $x^2$")
        backspace()  // the chip turns back into `$x^2$` text…
        XCTAssertEqual(message, "a $x^2$")
        backspace()  // …so only the closing `$` goes now
        XCTAssertEqual(message, "a $x^2")
    }

    func testLaterBackspaceDeletesTheWholeChip() {
        type("a $y$ b")
        XCTAssertEqual(message, "a $y$ b")
        for _ in 0..<3 { backspace() }  // "b", the space, then the chip as one character
        XCTAssertEqual(message, "a ")
    }

    func testMoneyAndSpacedDollarsStayText() {
        type("giá 5$ và $ 3$")
        XCTAssertEqual(message, "giá 5$ và $ 3$")
    }

    func testTheSymbolBarTypesUnicode() {
        type("AB")
        app.buttons["toggleSymbols"].tap()
        XCTAssertTrue(app.descendants(matching: .any)["symbolBar"].waitForExistence(timeout: 5))
        app.buttons["Vuông góc"].tap()
        type("CD")
        XCTAssertEqual(message, "AB⊥CD")
    }

    func testTheFormulaEditorInsertsAChipAndPlainUnicodeWhenItCan() {
        type("Tính")
        app.buttons["openFormula"].tap()
        let latex = app.textFields["latexField"].exists ? app.textFields["latexField"] : app.textViews["latexField"]
        XCTAssertTrue(latex.waitForExistence(timeout: 5))
        latex.typeText("BC^2=AB^2+AC^2")
        app.buttons["insertFormula"].tap()
        XCTAssertEqual(message, "Tính BC²=AB²+AC² ")

        app.buttons["openFormula"].tap()
        XCTAssertTrue(latex.waitForExistence(timeout: 5))
        latex.typeText("\\frac{1}{2}")
        app.buttons["insertFormula"].tap()
        XCTAssertEqual(message, "Tính BC²=AB²+AC² $\\frac{1}{2}$ ")
    }

    func testAMessageWithAFormulaIsSentAsLatex() {
        type("Giải phương trình $x+1=3$")
        app.buttons["send"].tap()
        let predicate = NSPredicate(format: "label CONTAINS %@", "Mình cùng đọc kỹ đề nhé")
        XCTAssertTrue(app.staticTexts.matching(predicate).firstMatch.waitForExistence(timeout: 20))
        XCTAssertEqual(message, "", "the box is emptied after sending")
    }
}
