import UIKit

/// A formula chip in the message box: the text holds U+FFFC, the LaTeX lives here.
final class FormulaAttachment: NSTextAttachment {
    let latex: String

    @MainActor
    init(latex: String, font: UIFont, traits: UITraitCollection) {
        self.latex = latex
        super.init(data: nil, ofType: nil)
        let color = UIColor.label.resolvedColor(with: traits)
        let padding = CGSize(width: 3, height: 2)
        if let math = MathRenderer.render(latex, fontSize: font.pointSize * MathRenderer.scale, color: color) {
            let size = CGSize(width: math.image.size.width + padding.width * 2,
                              height: math.image.size.height + padding.height * 2)
            let tint = UIColor.tintColor.resolvedColor(with: traits).withAlphaComponent(0.12)
            image = UIGraphicsImageRenderer(size: size).image { _ in
                tint.setFill()
                UIBezierPath(roundedRect: CGRect(origin: .zero, size: size), cornerRadius: 5).fill()
                math.image.draw(at: CGPoint(x: padding.width, y: padding.height))
            }
            bounds = CGRect(x: 0, y: -math.descent - padding.height, width: size.width, height: size.height)
        } else {
            // A formula SwiftMath cannot draw shows its source, like KaTeX's errors on the web.
            let text = "$\(latex)$" as NSString
            let attributes: [NSAttributedString.Key: Any] = [
                .font: UIFont.monospacedSystemFont(ofSize: font.pointSize * 0.9, weight: .regular),
                .foregroundColor: UIColor.systemRed.resolvedColor(with: traits),
            ]
            let size = text.size(withAttributes: attributes)
            image = UIGraphicsImageRenderer(size: size).image { _ in text.draw(at: .zero, withAttributes: attributes) }
            bounds = CGRect(x: 0, y: font.descender, width: size.width, height: size.height)
        }
        accessibilityLabel = LatexToPlain.plain(latex) ?? latex
    }

    required init?(coder: NSCoder) { fatalError("not used") }
}

/// Message text (`$latex$` formulas, `\n` line breaks) to and from the message box's content.
/// web: lib/messageText.ts `toMessageText` and useMathEditor's `fromMessageText`.
enum MessageTextCodec {
    /// A piece of a message: text, or a formula.
    enum Piece: Equatable { case text(String), formula(String) }

    /// `$$…$$` or `$…$` in a stored message (the edit box loads these as chips).
    private static let messageFormula = try! NSRegularExpression(pattern: #"\$\$([^$]+?)\$\$|\$([^$\n]+?)\$"#)
    /// `$…$` typed or pasted: not after a letter, digit, `\` or `$` ("5$"), and no space right
    /// inside the opening sign ("$ 3"). Group 1 is the character before it.
    static let pastedFormula = try! NSRegularExpression(pattern: #"(^|[^$\\\w])\$([^$\s][^$\n]*?)\$(?!\$)"#)
    /// The same, closed just before the caret.
    static let typedFormula = try! NSRegularExpression(pattern: #"(^|[^$\\\w])\$([^$\s][^$\n]*?)\$$"#)

    /// The message for the box's content: chips become `$latex$`.
    static func messageText(from content: NSAttributedString) -> String {
        var out = ""
        content.enumerateAttributes(in: NSRange(location: 0, length: content.length)) { attributes, range, _ in
            if let formula = attributes[.attachment] as? FormulaAttachment {
                out += "$\(formula.latex)$"
            } else {
                out += (content.string as NSString).substring(with: range).replacingOccurrences(of: "\u{FFFC}", with: "")
            }
        }
        return out
    }

    /// A stored message as pieces (every `$…$` and `$$…$$` is a formula).
    static func pieces(ofMessage text: String) -> [Piece] {
        pieces(text, regex: messageFormula) { match, ns in
            let group = match.range(at: 1).location != NSNotFound ? match.range(at: 1) : match.range(at: 2)
            return (match.range, ns.substring(with: group).trimmingCharacters(in: .whitespaces))
        }
    }

    /// Pasted text as pieces (only `$…$` that looks like a formula, as when typing).
    static func pieces(ofPasted text: String) -> [Piece] {
        pieces(text, regex: pastedFormula) { match, ns in
            let start = match.range(at: 1).upperBound  // keep the character before `$`
            return (NSRange(location: start, length: match.range.upperBound - start), ns.substring(with: match.range(at: 2)))
        }
    }

    private static func pieces(_ text: String, regex: NSRegularExpression,
                               formula: (NSTextCheckingResult, NSString) -> (NSRange, String)) -> [Piece] {
        let ns = text as NSString
        var pieces: [Piece] = []
        var last = 0
        for match in regex.matches(in: text, range: NSRange(location: 0, length: ns.length)) {
            let (range, latex) = formula(match, ns)
            if range.location > last { pieces.append(.text(ns.substring(with: NSRange(location: last, length: range.location - last)))) }
            pieces.append(.formula(latex))
            last = range.upperBound
        }
        if last < ns.length { pieces.append(.text(ns.substring(from: last))) }
        return pieces
    }
}
