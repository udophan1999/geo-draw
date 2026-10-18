import Foundation

/// Simple LaTeX as plain Unicode (`BC^2=AB^2+AC^2` → `BC²=AB²+AC²`), so the message box shows
/// readable text instead of a formula chip. nil when Unicode cannot write it cleanly
/// (fractions, long roots…). A port of web/src/lib/plainMath.ts; both pass
/// shared/fixtures/math_cases.json.
enum LatexToPlain {
    private static let superscript: [Character: String] = [
        "0": "⁰", "1": "¹", "2": "²", "3": "³", "4": "⁴", "5": "⁵", "6": "⁶", "7": "⁷", "8": "⁸", "9": "⁹",
        "+": "⁺", "-": "⁻", "(": "⁽", ")": "⁾", "n": "ⁿ", "x": "ˣ",
    ]
    private static let `subscript`: [Character: String] = [
        "0": "₀", "1": "₁", "2": "₂", "3": "₃", "4": "₄", "5": "₅", "6": "₆", "7": "₇", "8": "₈", "9": "₉",
        "+": "₊", "-": "₋", "n": "ₙ",
    ]
    private static let commands: [String: String] = [
        "cdot": "·", "times": "×", "div": "÷", "le": "≤", "leq": "≤", "ge": "≥", "geq": "≥", "ne": "≠", "neq": "≠",
        "pm": "±", "approx": "≈", "pi": "π", "angle": "∠", "widehat": "∠", "triangle": "△", "perp": "⊥",
        "parallel": "∥", "alpha": "α", "beta": "β", "gamma": "γ", "Delta": "Δ", "delta": "δ", "infty": "∞",
        "Rightarrow": "⇒", "Leftrightarrow": "⇔", "in": "∈", "notin": "∉", "subset": "⊂", "cup": "∪", "cap": "∩",
        "emptyset": "∅", "varnothing": "∅", "sim": "∽", "circ": "°", "degree": "°", "left": "", "right": "",
    ]

    private static let spacing = regex(#"\\(?:,|;|:|!|\s)"#)
    private static let degree = regex(#"\^\{?\\circ\}?"#)
    private static let textCommand = regex(#"\\(?:text|mathrm)\{([^{}]*)\}"#)
    private static let angle = regex(#"\\widehat\{([A-Za-z]{1,3})\}"#)
    private static let command = regex(#"\\([A-Za-z]+) ?"#)
    private static let script = regex(#"([\^_])(?:\{([^{}]*)\}|(.))"#)
    private static let leftover = regex(#"[\\{}^_]"#)

    static func plain(_ latex: String) -> String? {
        var text = replace(spacing, in: latex) { _ in " " }
        text = replace(degree, in: text) { _ in "°" }
        text = replace(textCommand, in: text) { $0[1] ?? "" }
        // Roots stay formulas: as text, √123 or √x+1 does not show where the root ends.
        text = replace(angle, in: text) { "∠" + ($0[1] ?? "") }  // "góc A"
        // A space after a command only ends its name in LaTeX ("\perp BC"): drop it.
        text = replace(command, in: text) { groups in commands[groups[1] ?? ""] ?? groups[0]! }
        var failed = false
        text = replace(script, in: text) { groups in
            let table = groups[1] == "^" ? superscript : `subscript`
            let body = groups[2] ?? groups[3] ?? ""
            let converted = body.map { table[$0] }
            if converted.contains(where: { $0 == nil }) { failed = true; return "" }
            return converted.compactMap { $0 }.joined()
        }
        if failed || leftover.firstMatch(in: text, range: NSRange(text.startIndex..., in: text)) != nil { return nil }
        return text.split(whereSeparator: \.isWhitespace).joined(separator: " ")
    }

    // MARK: Regex helpers (UTF-16 offsets, like the JavaScript original)

    private static func regex(_ pattern: String) -> NSRegularExpression { try! NSRegularExpression(pattern: pattern) }

    /// Replaces every match; `transform` gets the whole match and the groups (nil when unmatched).
    private static func replace(_ regex: NSRegularExpression, in text: String,
                                transform: ([String?]) -> String) -> String {
        var out = ""
        var last = text.startIndex
        for match in regex.matches(in: text, range: NSRange(text.startIndex..., in: text)) {
            guard let range = Range(match.range, in: text) else { continue }
            let groups = (0..<match.numberOfRanges).map { index in
                Range(match.range(at: index), in: text).map { String(text[$0]) }
            }
            out += text[last..<range.lowerBound]
            out += transform(groups)
            last = range.upperBound
        }
        out += text[last...]
        return out
    }
}
