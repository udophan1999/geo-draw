package com.tvcsoft.mathmate.core.math

/**
 * Message text (`$latex$` formulas, `\n` line breaks) and the pieces of the message box.
 * web: lib/messageText.ts `toMessageText` and useMathEditor's `fromMessageText`; iOS:
 * MessageTextCodec. All pass shared/fixtures/math_cases.json.
 */
object MessageTextCodec {
    /** A piece of a message: text, or a formula. */
    sealed interface Piece {
        data class Text(val text: String) : Piece
        data class Formula(val latex: String) : Piece
    }

    /** `$$…$$` or `$…$` in a stored message (the edit box loads these as chips). */
    private val messageFormula = Regex("""\$\$([^$]+?)\$\$|\$([^$\n]+?)\$""")

    /**
     * `$…$` typed or pasted: not after a letter, digit, `\` or `$` ("5$"), and no space right
     * inside the opening sign ("$ 3"). Group 1 is the character before it.
     */
    val pastedFormula = Regex("""(^|[^$\\\w])\$([^$\s][^$\n]*?)\$(?!\$)""")

    /** The same, closed just before the caret. */
    val typedFormula = Regex("""(^|[^$\\\w])\$([^$\s][^$\n]*?)\$$""")

    /** The message for the box's pieces: formulas become `$latex$`. */
    fun messageText(pieces: List<Piece>): String = pieces.joinToString("") { piece ->
        when (piece) {
            is Piece.Text -> piece.text
            is Piece.Formula -> "$${piece.latex}$"
        }
    }

    /** A stored message as pieces (every `$…$` and `$$…$$` is a formula). */
    fun piecesOfMessage(text: String): List<Piece> = pieces(text, messageFormula) { match ->
        val latex = match.groups[1]?.value ?: match.groups[2]?.value ?: ""
        match.range to latex.trim()
    }

    /** Pasted text as pieces (only `$…$` that looks like a formula, as when typing). */
    fun piecesOfPasted(text: String): List<Piece> = pieces(text, pastedFormula) { match ->
        val start = match.groups[1]!!.range.last + 1 // keep the character before `$`
        (start..match.range.last) to match.groupValues[2]
    }

    private fun pieces(text: String, regex: Regex, formula: (MatchResult) -> Pair<IntRange, String>): List<Piece> {
        val out = mutableListOf<Piece>()
        var last = 0
        for (match in regex.findAll(text)) {
            val (range, latex) = formula(match)
            if (range.first > last) out.add(Piece.Text(text.substring(last, range.first)))
            out.add(Piece.Formula(latex))
            last = range.last + 1
        }
        if (last < text.length) out.add(Piece.Text(text.substring(last)))
        return out
    }
}
