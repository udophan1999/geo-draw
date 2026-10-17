import Foundation

/// Makes model-written math safe to render, exactly like web/src/lib/math.ts `normalizeMath`
/// (both pass shared/fixtures/math_cases.json). The AI often writes `$$…$$` mid-sentence,
/// `\[…\]` and `\(…\)`, and `\tag{n}`. Code spans and fenced code blocks are left untouched.
enum MathNormalizer {
    private static let code = regex(#"(```[\s\S]*?```|`[^`\n]*`)"#)
    private static let displayBrackets = regex(#"\\\[([\s\S]+?)\\\]"#)
    private static let inlineParens = regex(#"\\\(([\s\S]+?)\\\)"#)
    private static let displayDollars = regex(#"\$\$([\s\S]+?)\$\$"#)
    private static let tag = regex(#"\\tag\*?\{([^}]*)\}"#)
    private static let blankLines = regex(#"\n{3,}"#)

    static func normalize(_ text: String) -> String {
        var out = ""
        var last = text.startIndex
        // Odd pieces are code (as `split` with a capturing group gives them in JavaScript).
        for match in matches(code, in: text) {
            out += fix(String(text[last..<match.range.lowerBound]))
            out += text[match.range]
            last = match.range.upperBound
        }
        out += fix(String(text[last...]))
        return out.trimmingCharacters(in: .whitespacesAndNewlines)
    }

    private static func fix(_ text: String) -> String {
        var text = replace(displayBrackets, in: text) { "\n\n$$\n\($0.trimmed)\n$$\n\n" }
        text = replace(inlineParens, in: text) { "$\($0.trimmed)$" }
        text = replace(displayDollars, in: text) { "\n\n$$\n\($0.trimmed)\n$$\n\n" }
        text = replace(tag, in: text) { "\\qquad (\($0))" }
        return replace(blankLines, in: text) { _ in "\n\n" }
    }

    // MARK: Regex helpers (NSRegularExpression, so `$` in replacements needs no escaping)

    private static func regex(_ pattern: String) -> NSRegularExpression {
        try! NSRegularExpression(pattern: pattern)
    }

    private struct Match { let range: Range<String.Index>; let group: String }

    private static func matches(_ regex: NSRegularExpression, in text: String) -> [Match] {
        regex.matches(in: text, range: NSRange(text.startIndex..., in: text)).compactMap { result in
            guard let range = Range(result.range, in: text) else { return nil }
            let group = result.numberOfRanges > 1 ? Range(result.range(at: 1), in: text).map { String(text[$0]) } : nil
            return Match(range: range, group: group ?? "")
        }
    }

    /// Replaces every match with `transform(first group)`.
    private static func replace(_ regex: NSRegularExpression, in text: String,
                                with transform: (String) -> String) -> String {
        var out = ""
        var last = text.startIndex
        for match in matches(regex, in: text) {
            out += text[last..<match.range.lowerBound]
            out += transform(match.group)
            last = match.range.upperBound
        }
        out += text[last...]
        return out
    }
}

private extension String {
    var trimmed: String { trimmingCharacters(in: .whitespacesAndNewlines) }
}
