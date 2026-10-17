import XCTest

/// The figure of a geometry problem, drawn for real by the parser (no AI) on the test server.
@MainActor
final class DrawingTests: XCTestCase {
    private var app: XCUIApplication!

    override func setUp() async throws {
        continueAfterFailure = false
        app = XCUIApplication()
        let api = ProcessInfo.processInfo.environment["MATHMATE_TEST_API"] ?? "http://127.0.0.1:8797"
        app.launchArguments = ["-uiTesting", "-api", api]
        app.launch()
        XCTAssertTrue(app.buttons["tryAsGuest"].waitForExistence(timeout: 10))
        app.buttons["tryAsGuest"].tap()
        useParser()
        app.buttons["newConversation"].tap()
    }

    /// Settings → "Parser nhanh": figures are drawn on the server without the AI.
    private func useParser() {
        XCTAssertTrue(app.buttons["accountMenu"].waitForExistence(timeout: 10))
        app.buttons["accountMenu"].tap()
        app.buttons["Cài đặt"].tap()
        let parser = app.buttons["Parser nhanh"]
        XCTAssertTrue(parser.waitForExistence(timeout: 10))
        parser.tap()
        app.buttons["Lưu"].tap()
        XCTAssertTrue(app.buttons["newConversation"].waitForExistence(timeout: 10))
    }

    private func label(_ identifier: String) -> String {
        app.descendants(matching: .any)[identifier].label
    }

    func testAGeometryProblemIsDrawnAndCanBeRefined() {
        let composer = app.textViews["composer"]
        XCTAssertTrue(composer.waitForExistence(timeout: 10))
        composer.tap()
        composer.typeText("Cho tam giác ABC vuông tại A, AB = 3, AC = 4.")
        app.buttons["send"].tap()

        // The card in the chat shows the drawing once the server has drawn it.
        let ready = app.staticTexts["Chạm để xem, phóng to, chỉnh hình"]
        XCTAssertTrue(ready.waitForExistence(timeout: 120), "the figure is drawn")
        app.descendants(matching: .any)["figureCard"].firstMatch.tap()

        let version = app.descendants(matching: .any)["drawingVersion"]
        XCTAssertTrue(version.waitForExistence(timeout: 10))
        XCTAssertEqual(version.label, "Phiên bản mới nhất")
        XCTAssertTrue(app.descendants(matching: .any)["drawingImage"].firstMatch.exists)
        // ShareLink is not a plain button in the accessibility tree.
        XCTAssertTrue(app.descendants(matching: .any)["shareDrawing"].firstMatch.waitForExistence(timeout: 10))

        // A refinement draws a second version; the first stays one tap away.
        let refine = app.textFields["refineField"]
        refine.tap()
        refine.typeText("Vẽ đường cao AH")
        app.buttons["sendRefine"].tap()
        XCTAssertTrue(app.buttons["version-2"].waitForExistence(timeout: 120), "the refined figure is drawn")
        XCTAssertTrue(app.staticTexts["Đã yêu cầu: “Vẽ đường cao AH”"].exists)
        app.buttons["version-1"].tap()
        XCTAssertEqual(label("drawingVersion"), "Phiên bản 1/2")
    }
}
