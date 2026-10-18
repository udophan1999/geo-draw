package com.tvcsoft.mathmate.core.math

/**
 * Simple LaTeX as plain Unicode (`BC^2=AB^2+AC^2` → `BC²=AB²+AC²`), so the message box shows
 * readable text instead of a formula chip. null when Unicode cannot write it cleanly
 * (fractions, long roots…). A port of web/src/lib/plainMath.ts; web, iOS and Android pass
 * shared/fixtures/math_cases.json.
 */
object LatexToPlain {
    private val superscript = mapOf(
        '0' to "⁰", '1' to "¹", '2' to "²", '3' to "³", '4' to "⁴", '5' to "⁵", '6' to "⁶", '7' to "⁷", '8' to "⁸",
        '9' to "⁹", '+' to "⁺", '-' to "⁻", '(' to "⁽", ')' to "⁾", 'n' to "ⁿ", 'x' to "ˣ",
    )
    private val subscript = mapOf(
        '0' to "₀", '1' to "₁", '2' to "₂", '3' to "₃", '4' to "₄", '5' to "₅", '6' to "₆", '7' to "₇", '8' to "₈",
        '9' to "₉", '+' to "₊", '-' to "₋", 'n' to "ₙ",
    )
    private val commands = mapOf(
        "cdot" to "·", "times" to "×", "div" to "÷", "le" to "≤", "leq" to "≤", "ge" to "≥", "geq" to "≥",
        "ne" to "≠", "neq" to "≠", "pm" to "±", "approx" to "≈", "pi" to "π", "angle" to "∠", "widehat" to "∠",
        "triangle" to "△", "perp" to "⊥", "parallel" to "∥", "alpha" to "α", "beta" to "β", "gamma" to "γ",
        "Delta" to "Δ", "delta" to "δ", "infty" to "∞", "Rightarrow" to "⇒", "Leftrightarrow" to "⇔", "in" to "∈",
        "notin" to "∉", "subset" to "⊂", "cup" to "∪", "cap" to "∩", "emptyset" to "∅", "varnothing" to "∅",
        "sim" to "∽", "circ" to "°", "degree" to "°", "left" to "", "right" to "",
    )

    private val spacing = Regex("""\\(?:,|;|:|!|\s)""")
    private val degree = Regex("""\^\{?\\circ\}?""")
    private val textCommand = Regex("""\\(?:text|mathrm)\{([^{}]*)\}""")
    private val shortRoot = Regex("""\\sqrt\{([A-Za-z0-9]{1,3})\}""")
    private val angle = Regex("""\\widehat\{([A-Za-z]{1,3})\}""")
    private val command = Regex("""\\([A-Za-z]+) ?""")
    private val script = Regex("""([\^_])(?:\{([^{}]*)\}|(.))""")
    private val leftover = Regex("""[\\{}^_]""")
    private val whitespace = Regex("""\s+""")

    fun plain(latex: String): String? {
        var text = spacing.replace(latex) { " " }
        text = degree.replace(text) { "°" }
        text = textCommand.replace(text) { it.groupValues[1] }
        // \sqrt{x} with a short plain body: √x (√(…) for longer ones would read ambiguously).
        text = shortRoot.replace(text) { "√" + it.groupValues[1] }
        text = angle.replace(text) { "∠" + it.groupValues[1] } // "góc A"
        // A space after a command only ends its name in LaTeX ("\perp BC"): drop it.
        text = command.replace(text) { commands[it.groupValues[1]] ?: it.value }
        var failed = false
        text = script.replace(text) { match ->
            val table = if (match.groupValues[1] == "^") superscript else subscript
            val body = match.groups[2]?.value ?: match.groups[3]?.value ?: ""
            val converted = body.map { table[it] }
            if (converted.any { it == null }) {
                failed = true
                ""
            } else {
                converted.joinToString("")
            }
        }
        if (failed || leftover.containsMatchIn(text)) return null
        return text.trim().split(whitespace).filter { it.isNotEmpty() }.joinToString(" ")
    }
}
