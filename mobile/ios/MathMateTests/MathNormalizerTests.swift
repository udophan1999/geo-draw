import Foundation
import Testing
@testable import MathMate

/// shared/fixtures/math_cases.json: the same cases web/e2e/shared-fixtures.spec.ts runs.
struct SharedFixtures: Decodable {
    struct Case: Decodable { let input: String; let expected: String }
    struct PlainCase: Decodable { let input: String; let expected: String? }
    /// A paragraph of the message box: text, a formula, or a line break.
    struct Piece: Decodable { let text: String?; let math: String?; let `break`: Bool? }
    struct MessageCase: Decodable { let blocks: [[Piece]]; let expected: String }
    let normalizeMath: [Case]
    let latexToPlain: [PlainCase]
    let toMessageText: [MessageCase]

    static func load() throws -> SharedFixtures {
        let bundle = Bundle(for: FixtureToken.self)
        let url = try #require(bundle.url(forResource: "math_cases", withExtension: "json"))
        return try JSONDecoder().decode(SharedFixtures.self, from: Data(contentsOf: url))
    }
}

private final class FixtureToken {}

struct MathNormalizerTests {
    @Test func matchesTheWebOnEverySharedCase() throws {
        let cases = try SharedFixtures.load().normalizeMath
        #expect(!cases.isEmpty)
        for item in cases {
            #expect(MathNormalizer.normalize(item.input) == item.expected, "\(item.input)")
        }
    }
}

struct LatexToPlainTests {
    @Test func matchesTheWebOnEverySharedCase() throws {
        for item in try SharedFixtures.load().latexToPlain {
            #expect(LatexToPlain.plain(item.input) == item.expected, "\(item.input)")
        }
    }
}

@MainActor
struct MessageTextCodecTests {
    /// The fixtures' paragraphs as the message box's content (paragraphs and breaks are both
    /// line breaks in the box).
    private func content(_ blocks: [[SharedFixtures.Piece]]) -> NSAttributedString {
        let view = MathTextView()
        let out = NSMutableAttributedString()
        for (index, block) in blocks.enumerated() {
            if index > 0 { out.append(view.plain("\n")) }
            for piece in block {
                if let latex = piece.math { out.append(view.chip(latex)) }
                else if piece.break == true { out.append(view.plain("\n")) }
                else { out.append(view.plain(piece.text ?? "")) }
            }
        }
        return out
    }

    @Test func matchesTheWebOnEverySharedCase() throws {
        for item in try SharedFixtures.load().toMessageText {
            #expect(MessageTextCodec.messageText(from: content(item.blocks)) == item.expected)
        }
    }

    @Test func aStoredMessageLoadsBackAsChips() {
        let view = MathTextView()
        view.load("Cho $\\triangle ABC$ có $$AB = 3$$ và 5$ tiền")
        #expect(view.messageText == "Cho $\\triangle ABC$ có $AB = 3$ và 5$ tiền")
        var chips = 0
        view.textStorage.enumerateAttribute(.attachment, in: NSRange(location: 0, length: view.textStorage.length)) { value, _, _ in
            if value is FormulaAttachment { chips += 1 }
        }
        #expect(chips == 2)
    }

    @Test func pastedTextKeepsMoneyAndSpacedDollarsAsText() {
        #expect(MessageTextCodec.pieces(ofPasted: "a $x^2$ b") == [.text("a "), .formula("x^2"), .text(" b")])
        #expect(MessageTextCodec.pieces(ofPasted: "giá 5$ và $ 3$") == [.text("giá 5$ và $ 3$")])
        #expect(MessageTextCodec.pieces(ofPasted: "$a$") == [.formula("a")])
    }

    @Test func aFormulaIsPlainUnicodeWhenItCanBeAndAlwaysSpacedOut() {
        let view = MathTextView()
        view.load("Tính")
        view.insertFormula("BC^2=AB^2+AC^2")
        #expect(view.messageText == "Tính BC²=AB²+AC² ")
        view.insertFormula("\\frac{1}{2}")
        #expect(view.messageText == "Tính BC²=AB²+AC² $\\frac{1}{2}$ ")
    }
}
