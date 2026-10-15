// Typesets every formula of a JSON list with SwiftMath and reports what fails.
//
//   [MATH_FONT=<bundled font name>] swift run MathSpike <formulas.json> <output folder>
//
// formulas.json: [{"id": "...", "latex": "..."}]. Writes <output>/<id>.png for each formula
// that renders, and <output>/report.json with the parse errors.
import AppKit
import Foundation
import SwiftMath

struct Formula: Decodable { let id: String; let latex: String }
struct Outcome: Encodable { let id: String; let latex: String; let error: String? }

let arguments = CommandLine.arguments
guard arguments.count == 3 else {
    print("Cách dùng: swift run MathSpike <formulas.json> <thư mục kết quả>")
    exit(2)
}
let formulas = try JSONDecoder().decode([Formula].self,
                                        from: Data(contentsOf: URL(fileURLWithPath: arguments[1])))
let output = URL(fileURLWithPath: arguments[2], isDirectory: true)
try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)

// MATH_FONT picks one of SwiftMath's bundled fonts (e.g. texgyretermes-math); default Latin Modern.
let mathFont = ProcessInfo.processInfo.environment["MATH_FONT"]
    .flatMap { MTFontManager().font(withName: $0, size: 28) }

var outcomes: [Outcome] = []
for formula in formulas {
    var parseError: NSError?
    _ = MTMathListBuilder.build(fromString: formula.latex, error: &parseError)
    var message = parseError?.localizedDescription
    if message == nil {
        let image = MTMathImage(latex: formula.latex, fontSize: 28, textColor: .black,
                                labelMode: .text)
        if let mathFont { image.font = mathFont }
        image.contentInsets = MTEdgeInsets(top: 6, left: 6, bottom: 6, right: 6)
        let (renderError, rendered) = image.asImage()
        if let renderError {
            message = "render: \(renderError.localizedDescription)"
        } else if let rendered, let tiff = rendered.tiffRepresentation,
                  let png = NSBitmapImageRep(data: tiff)?.representation(using: .png, properties: [:]) {
            try png.write(to: output.appendingPathComponent("\(formula.id).png"))
        }
    }
    outcomes.append(Outcome(id: formula.id, latex: formula.latex, error: message))
}

let encoder = JSONEncoder()
encoder.outputFormatting = [.prettyPrinted, .sortedKeys, .withoutEscapingSlashes]
try encoder.encode(outcomes).write(to: output.appendingPathComponent("report.json"))
let failed = outcomes.filter { $0.error != nil }
print("\(outcomes.count - failed.count)/\(outcomes.count) công thức render được")
for outcome in failed { print("✘ \(outcome.id): \(outcome.latex)  →  \(outcome.error!)") }
