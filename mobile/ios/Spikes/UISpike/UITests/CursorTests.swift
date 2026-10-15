import XCTest

/// Tapping a formula puts the caret in the part tapped (MTDisplay+Editing in the fork).
@MainActor
final class CursorTests: XCTestCase {
    private var app: XCUIApplication!

    override func setUp() async throws {
        continueAfterFailure = false
        app = XCUIApplication()
        app.launchArguments = ["-screen", "cursor"]
        app.launch()
    }

    private func tap(_ dx: CGFloat, _ dy: CGFloat) -> String {
        app.otherElements["formula"].coordinate(withNormalizedOffset: CGVector(dx: dx, dy: dy)).tap()
        return app.staticTexts["caretIndex"].label
    }

    /// Index descriptions: "[atom, type:sub]" with type 4 = numerator, 5 = denominator,
    /// 6 = radicand, 7 = degree, 2 = superscript, 3 = subscript.
    func testTapsLandInTheRightPart() throws {
        let numerator = tap(0.70, 0.40)
        if let path = ProcessInfo.processInfo.environment["SPIKE_SCREENSHOT"] {
            try XCUIScreen.main.screenshot().pngRepresentation.write(to: URL(fileURLWithPath: path))
        }
        // x_{1,2} = \frac{-b ± \sqrt{Δ}}{2a}: the fraction takes the right part of the view.
        XCTAssertTrue(numerator.contains("4:"), "numerator: \(numerator)")
        let denominator = tap(0.70, 0.62)
        XCTAssertTrue(denominator.contains("5:"), "denominator: \(denominator)")
        XCTAssertEqual(tap(0.02, 0.5), "[0]", "far left: before everything")
    }
}
