package com.tvcsoft.mathmate.core.math

/**
 * Makes model-written math safe to render, exactly like web/src/lib/math.ts `normalizeMath`
 * (both pass shared/fixtures/math_cases.json, as does the iOS MathNormalizer). The AI often
 * writes `$$…$$` mid-sentence, `\[…\]` and `\(…\)`, and `\tag{n}`. Code spans and fenced code
 * blocks are left untouched.
 */
object MathNormalizer {
    private val code = Regex("""(```[\s\S]*?```|`[^`\n]*`)""")
    private val displayBrackets = Regex("""\\\[([\s\S]+?)\\\]""")
    private val inlineParens = Regex("""\\\(([\s\S]+?)\\\)""")
    private val displayDollars = Regex("""\$\$([\s\S]+?)\$\$""")
    private val tag = Regex("""\\tag\*?\{([^}]*)\}""")
    private val blankLines = Regex("""\n{3,}""")

    fun normalize(text: String): String {
        val out = StringBuilder()
        var last = 0
        // Code is copied as it is (as `split` with a capturing group gives it in JavaScript).
        for (match in code.findAll(text)) {
            out.append(fix(text.substring(last, match.range.first)))
            out.append(match.value)
            last = match.range.last + 1
        }
        out.append(fix(text.substring(last)))
        return out.toString().trim()
    }

    private fun fix(text: String): String {
        var out = displayBrackets.replace(text) { "\n\n$$\n${it.groupValues[1].trim()}\n$$\n\n" }
        out = inlineParens.replace(out) { "$${it.groupValues[1].trim()}$" }
        out = displayDollars.replace(out) { "\n\n$$\n${it.groupValues[1].trim()}\n$$\n\n" }
        out = tag.replace(out) { "\\qquad (${it.groupValues[1]})" }
        return blankLines.replace(out) { "\n\n" }
    }
}
