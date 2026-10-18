package com.tvcsoft.mathmate

import com.tvcsoft.mathmate.core.jobs.JobEvent
import com.tvcsoft.mathmate.core.jobs.SseParser
import com.tvcsoft.mathmate.core.math.LatexToPlain
import com.tvcsoft.mathmate.core.math.MathBlocks
import com.tvcsoft.mathmate.core.math.MathBlocks.Block
import com.tvcsoft.mathmate.core.math.MathBlocks.Line
import com.tvcsoft.mathmate.core.math.MathNormalizer
import com.tvcsoft.mathmate.core.math.MessageTextCodec
import com.tvcsoft.mathmate.core.math.MessageTextCodec.Piece
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.boolean
import kotlinx.serialization.json.jsonArray
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNull
import org.junit.Test
import java.io.File

/** The cases the web (e2e/shared-fixtures.spec.ts) and iOS (MathNormalizerTests) pass too. */
class SharedFixturesTest {
    private val fixtures = Json.parseToJsonElement(File("../../../shared/fixtures/math_cases.json").readText()).jsonObject

    private fun cases(name: String) = fixtures.getValue(name).jsonArray.map { it.jsonObject }

    @Test
    fun normalizeMathMatchesTheWeb() {
        for (case in cases("normalizeMath")) {
            val input = case.getValue("input").jsonPrimitive.content
            assertEquals(input, case.getValue("expected").jsonPrimitive.content, MathNormalizer.normalize(input))
        }
    }

    @Test
    fun latexToPlainMatchesTheWeb() {
        for (case in cases("latexToPlain")) {
            val input = case.getValue("input").jsonPrimitive.content
            val expected = case["expected"]?.jsonPrimitive?.takeUnless { it.content == "null" && !it.isString }?.content
            assertEquals(input, expected, LatexToPlain.plain(input))
        }
    }

    @Test
    fun messageTextMatchesTheWeb() {
        for (case in cases("toMessageText")) {
            val pieces = mutableListOf<Piece>()
            case.getValue("blocks").jsonArray.forEachIndexed { index, block ->
                if (index > 0) pieces.add(Piece.Text("\n"))
                for (element in block.jsonArray) {
                    val piece = element as JsonObject
                    when {
                        piece["math"] != null -> pieces.add(Piece.Formula(piece.getValue("math").jsonPrimitive.content))
                        piece["break"]?.jsonPrimitive?.boolean == true -> pieces.add(Piece.Text("\n"))
                        else -> pieces.add(Piece.Text(piece["text"]?.jsonPrimitive?.content ?: ""))
                    }
                }
            }
            assertEquals(case.getValue("expected").jsonPrimitive.content, MessageTextCodec.messageText(pieces))
        }
    }
}

class MessageTextCodecTest {
    @Test
    fun aStoredMessageLoadsBackAsFormulas() {
        val pieces = MessageTextCodec.piecesOfMessage("Cho \$\\triangle ABC\$ có \$\$AB = 3\$\$ và 5\$ tiền")
        assertEquals(
            listOf(Piece.Text("Cho "), Piece.Formula("\\triangle ABC"), Piece.Text(" có "), Piece.Formula("AB = 3"), Piece.Text(" và 5\$ tiền")),
            pieces,
        )
        assertEquals("Cho \$\\triangle ABC\$ có \$AB = 3\$ và 5\$ tiền", MessageTextCodec.messageText(pieces))
    }

    @Test
    fun pastedTextKeepsMoneyAndSpacedDollarsAsText() {
        assertEquals(listOf(Piece.Text("a "), Piece.Formula("x^2"), Piece.Text(" b")), MessageTextCodec.piecesOfPasted("a \$x^2\$ b"))
        assertEquals(listOf(Piece.Text("giá 5\$ và \$ 3\$")), MessageTextCodec.piecesOfPasted("giá 5\$ và \$ 3\$"))
        assertEquals(listOf(Piece.Formula("a")), MessageTextCodec.piecesOfPasted("\$a\$"))
    }

    @Test
    fun aFormulaClosedBeforeTheCaretIsFound() {
        val match = MessageTextCodec.typedFormula.find("Tính \$x^2\$")!!
        assertEquals("x^2", match.groupValues[2])
        assertNull(MessageTextCodec.typedFormula.find("giá 5\$"))
    }
}

class MathBlocksTest {
    @Test
    fun paragraphsDisplayFormulasAndInlineMath() {
        val blocks = MathBlocks.parse("Ta có \$a^2\$ và **b**.\n\n\$\$\nx = 1\n\$\$\n\n- Bước \$1\$\n## Kết luận")
        assertEquals(
            listOf(
                Block.Paragraph(listOf(Line(Line.Kind.PLAIN, listOf(MathBlocks.Piece.Text("Ta có "), MathBlocks.Piece.Math("a^2"), MathBlocks.Piece.Text(" và **b**."))))),
                Block.Display("x = 1"),
                Block.Paragraph(
                    listOf(
                        Line(Line.Kind.BULLET, listOf(MathBlocks.Piece.Text("Bước "), MathBlocks.Piece.Math("1"))),
                        Line(Line.Kind.HEADING, listOf(MathBlocks.Piece.Text("Kết luận"))),
                    ),
                ),
            ),
            blocks,
        )
    }

    @Test
    fun unclosedFormulasAndMoneyStayText() {
        assertEquals(listOf(MathBlocks.Piece.Text("Còn \$x + 1")), MathBlocks.pieces("Còn \$x + 1"))
        assertEquals(listOf(MathBlocks.Piece.Text("giá 5 \$ và \$ 3")), MathBlocks.pieces("giá 5 \$ và \$ 3"))
        assertEquals(
            listOf(Block.Paragraph(listOf(Line(Line.Kind.PLAIN, listOf(MathBlocks.Piece.Text("Đang viết \$\$x+")))))),
            MathBlocks.parse("Đang viết \$\$x+"),
        )
    }
}

class SseParserTest {
    @Test
    fun eventsEndAtBlankLinesAndKeepAlivesAreIgnored() {
        val parser = SseParser()
        val lines = listOf(": keepalive", "", "event: delta", "data: {\"text\":\"Em \"}", "", "event: done", "data: {}", "")
        assertEquals(
            listOf(JobEvent("delta", "{\"text\":\"Em \"}"), JobEvent("done", "{}")),
            lines.mapNotNull { parser.feed(it) },
        )
    }

    @Test
    fun multiLineDataIsJoined() {
        val parser = SseParser()
        assertEquals(listOf(JobEvent("message", "a\nb")), listOf("event: message", "data: a", "data:b", "").mapNotNull { parser.feed(it) })
    }
}
