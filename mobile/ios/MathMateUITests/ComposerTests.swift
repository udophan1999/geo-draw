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

    // MARK: The visual formula editor

    /// The editor takes keys, so accessibility shows it as a text view.
    private var editorElement: XCUIElement { app.descendants(matching: .any)["formulaEditor"] }
    private var formula: String { editorElement.value as? String ?? "" }

    private func openFormula() {
        app.buttons["openFormula"].tap()
        XCTAssertTrue(editorElement.waitForExistence(timeout: 5))
    }

    private func keys(_ ids: String...) {
        for id in ids { app.buttons["key-\(id)"].tap() }
    }

    private func page(_ name: String) { app.buttons["page-\(name)"].tap() }

    func testAFractionFromTheKeyboardBecomesAChip() {
        type("Tính")
        openFormula()
        keys("frac", "1", "right", "2")
        XCTAssertEqual(formula, "\\frac{1}{2}")
        app.buttons["insertFormula"].tap()
        XCTAssertEqual(message, "Tính $\\frac{1}{2}$ ")
    }

    func testSimpleFormulasArriveAsUnicode() {
        openFormula()
        page("abc")
        keys("B", "C")
        page("123")
        keys("square", "=")
        page("abc")
        keys("A", "B")
        page("123")
        keys("square")
        XCTAssertEqual(formula, "BC^{2}=AB^{2}")
        app.buttons["insertFormula"].tap()
        XCTAssertEqual(message, "BC²=AB² ")
    }

    func testGeometryNotationIsEditableInside() {
        openFormula()
        page("Hình")
        keys("hat", "A", "B", "C")
        XCTAssertEqual(formula, "\\widehat{ABC}")
        app.buttons["insertFormula"].tap()
        XCTAssertEqual(message, "∠ABC ", "a simple angle becomes plain text")

        openFormula()
        page("Hình")
        keys("arc", "A", "B")
        XCTAssertEqual(formula, "\\overset{\\frown}{AB}")
        app.buttons["insertFormula"].tap()
        XCTAssertEqual(message, "∠ABC $\\overset{\\frown}{AB}$ ")
    }

    func testBackspaceGoesThroughTheStructure() {
        openFormula()
        keys("1", "frac", "2")  // 1 / 2: the 1 becomes the numerator
        XCTAssertEqual(formula, "\\frac{1}{2}")
        keys("backspace", "backspace")  // the 2, then back into the numerator
        keys("backspace", "backspace")  // the 1, then the empty fraction
        XCTAssertEqual(formula, "")
    }

    func testLatexCanBeTypedDirectly() {
        openFormula()
        app.buttons["toggleLatex"].tap()
        let latex = app.textFields["latexField"].exists ? app.textFields["latexField"] : app.textViews["latexField"]
        XCTAssertTrue(latex.waitForExistence(timeout: 5))
        latex.typeText("\\begin{cases}x=1\\\\y=2\\end{cases}")
        app.buttons["insertFormula"].tap()
        XCTAssertEqual(message, "$\\begin{cases}x=1\\\\y=2\\end{cases}$ ")
    }

    func testAMessageWithAFormulaIsSentAsLatex() {
        type("Giải phương trình $x+1=3$")
        app.buttons["send"].tap()
        let predicate = NSPredicate(format: "label CONTAINS %@", "Mình cùng đọc kỹ đề nhé")
        XCTAssertTrue(app.staticTexts.matching(predicate).firstMatch.waitForExistence(timeout: 20))
        XCTAssertEqual(message, "", "the box is emptied after sending")
    }
}
