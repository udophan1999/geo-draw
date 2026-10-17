import XCTest

/// The composer's chip rules, as in web/e2e/composer.spec.ts.
@MainActor
final class ComposerTests: XCTestCase {
    private var app: XCUIApplication!

    override func setUp() async throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments = ["-screen", "composer"]
        app.launch()
    }

    private var message: String { app.staticTexts["messageText"].label }

    private func typeAtEnd(_ text: String) {
        let box = app.textViews["composer"]
        box.tap()
        // Move the caret to the end: tap near the bottom-right corner of the box.
        box.coordinate(withNormalizedOffset: CGVector(dx: 0.98, dy: 0.95)).tap()
        box.typeText(text)
    }

    func testLoadedMessageComesBackUnchanged() {
        XCTAssertEqual(message, "Cho $\\triangle ABC$ có $AB = 3$ và $\\widehat{A} = 90^\\circ$. Tính $BC$.")
    }

    func testBackspaceRightAfterTypingGivesTheSourceBack() {
        typeAtEnd(" $x^2$")
        XCTAssertTrue(message.hasSuffix(" $x^2$"), message)
        app.keys["delete"].tap()  // the chip turns back into `$x^2$` text
        XCTAssertTrue(message.hasSuffix(" $x^2$"), message)
        app.keys["delete"].tap()  // now only the closing `$` goes
        XCTAssertTrue(message.hasSuffix(" $x^2"), message)
    }

    func testBackspaceLaterDeletesTheWholeChip() {
        typeAtEnd(" $y$ b")
        XCTAssertTrue(message.hasSuffix(" $y$ b"), message)
        for _ in 0..<3 { app.keys["delete"].tap() }  // "b", the space, then the chip as one
        XCTAssertTrue(message.hasSuffix("Tính $BC$. "), message)
    }
}
