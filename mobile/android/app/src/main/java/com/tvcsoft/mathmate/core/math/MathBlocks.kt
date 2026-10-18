package com.tvcsoft.mathmate.core.math

/**
 * Splits normalized message text into paragraphs, lines and formulas (the iOS MathBlocks; on
 * the web remark-math does this).
 */
object MathBlocks {
    sealed interface Piece {
        data class Text(val markdown: String) : Piece
        data class Math(val latex: String) : Piece
    }

    data class Line(val kind: Kind, val pieces: List<Piece>) {
        enum class Kind { PLAIN, BULLET, HEADING }
    }

    sealed interface Block {
        data class Paragraph(val lines: List<Line>) : Block
        data class Display(val latex: String) : Block
    }

    private val heading = Regex("""^#{1,6}\s+""")
    private val bullet = Regex("""^[-*+]\s+""")

    fun parse(text: String): List<Block> {
        val blocks = mutableListOf<Block>()
        var rest = text
        while (true) {
            val open = rest.indexOf("$$")
            if (open < 0) break
            val close = rest.indexOf("$$", open + 2)
            if (close < 0) break // unclosed (still streaming): text
            appendParagraphs(rest.substring(0, open), blocks)
            val latex = rest.substring(open + 2, close).trim()
            if (latex.isNotEmpty()) blocks.add(Block.Display(latex))
            rest = rest.substring(close + 2)
        }
        appendParagraphs(rest, blocks)
        return blocks
    }

    private fun appendParagraphs(text: String, blocks: MutableList<Block>) {
        for (paragraph in text.split("\n\n")) {
            val lines = paragraph.split("\n").map { it.trim() }.filter { it.isNotEmpty() }.map(::line)
            if (lines.isNotEmpty()) blocks.add(Block.Paragraph(lines))
        }
    }

    /** `- item` / `* item` become bullets and `## Title` a heading; numbered lists stay as typed. */
    fun line(text: String): Line {
        heading.find(text)?.let { return Line(Line.Kind.HEADING, pieces(text.substring(it.range.last + 1))) }
        bullet.find(text)?.let { return Line(Line.Kind.BULLET, pieces(text.substring(it.range.last + 1))) }
        return Line(Line.Kind.PLAIN, pieces(text))
    }

    /**
     * `$…$` with no space right inside the opening sign is a formula (as in remark-math);
     * a `$` with no closing one on the line stays text.
     */
    fun pieces(text: String): List<Piece> {
        val pieces = mutableListOf<Piece>()
        val buffer = StringBuilder()
        var index = 0
        while (index < text.length) {
            val next = index + 1
            val close = if (text[index] == '$' && next < text.length && !text[next].isWhitespace() && text[next] != '$') {
                text.indexOf('$', next).takeIf { it >= 0 }
            } else {
                null
            }
            if (close != null) {
                if (buffer.isNotEmpty()) {
                    pieces.add(Piece.Text(buffer.toString()))
                    buffer.clear()
                }
                pieces.add(Piece.Math(text.substring(next, close)))
                index = close + 1
            } else {
                buffer.append(text[index])
                index = next
            }
        }
        if (buffer.isNotEmpty()) pieces.add(Piece.Text(buffer.toString()))
        return pieces
    }
}
