package com.tvcsoft.mathmate.ui.math

import android.graphics.Canvas
import android.graphics.Paint
import android.graphics.Typeface
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.style.ForegroundColorSpan
import android.text.style.ReplacementSpan
import android.text.style.StyleSpan
import android.text.style.TypefaceSpan
import android.view.View
import android.widget.TextView
import androidx.compose.foundation.Image
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.requiredSize
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material3.LocalContentColor
import androidx.compose.material3.LocalTextStyle
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.text
import androidx.compose.ui.text.AnnotatedString
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import com.tvcsoft.mathmate.core.math.LatexToPlain
import com.tvcsoft.mathmate.core.math.MathBlocks
import com.tvcsoft.mathmate.core.math.MathNormalizer

/**
 * A formula inside a line of text, sitting on the baseline and wrapping with the words (the
 * iOS app's `Text(Image)` with a baseline offset). Lines grow to make room for tall formulas.
 */
class MathSpan(val latex: String, private val math: RenderedMath, private val background: Int? = null) : ReplacementSpan() {
    private val padX = if (background != null) 4 else 1

    override fun getSize(paint: Paint, text: CharSequence?, start: Int, end: Int, fm: Paint.FontMetricsInt?): Int {
        if (fm != null) {
            val font = paint.fontMetricsInt
            val ascent = -(math.ascent + RenderedMath.PAD).toInt() - 1
            val descent = (math.descent + RenderedMath.PAD).toInt() + 1
            fm.ascent = minOf(font.ascent, ascent)
            fm.top = minOf(font.top, ascent)
            fm.descent = maxOf(font.descent, descent)
            fm.bottom = maxOf(font.bottom, descent)
        }
        return math.width + padX * 2
    }

    override fun draw(canvas: Canvas, text: CharSequence?, start: Int, end: Int, x: Float, top: Int, y: Int, bottom: Int, paint: Paint) {
        background?.let { color ->
            val fill = Paint(Paint.ANTI_ALIAS_FLAG).apply { this.color = color }
            canvas.drawRoundRect(x, y - math.ascent - RenderedMath.PAD - 2, x + math.width + padX * 2, y + math.descent + RenderedMath.PAD + 2, 10f, 10f, fill)
        }
        canvas.drawBitmap(math.bitmap, x + padX, y - math.ascent - RenderedMath.PAD, null)
    }
}

/** Inline Markdown the tutor writes: **bold**, *italic*, `code`. */
private val markdown = Regex("""\*\*(.+?)\*\*|__(.+?)__|(?<![*\w])\*(?!\s)(.+?)\*(?!\w)|`([^`]+)`""")

private fun SpannableStringBuilder.appendMarkdown(text: String) {
    var last = 0
    for (match in markdown.findAll(text)) {
        append(text, last, match.range.first)
        val start = length
        val groups = match.groups
        when {
            groups[1] != null || groups[2] != null -> {
                append((groups[1] ?: groups[2])!!.value)
                setSpan(StyleSpan(Typeface.BOLD), start, length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            }
            groups[3] != null -> {
                append(groups[3]!!.value)
                setSpan(StyleSpan(Typeface.ITALIC), start, length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            }
            else -> {
                append(groups[4]!!.value)
                setSpan(TypefaceSpan("monospace"), start, length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            }
        }
        last = match.range.last + 1
    }
    append(text, last, text.length)
}

/** A paragraph's lines as styled text with formula spans. */
fun mathParagraph(lines: List<MathBlocks.Line>, fontPx: Float, color: Int, cursor: Boolean, cursorColor: Int): CharSequence {
    val out = SpannableStringBuilder()
    lines.forEachIndexed { index, line ->
        if (index > 0) out.append('\n')
        val lineStart = out.length
        if (line.kind == MathBlocks.Line.Kind.BULLET) out.append("•  ")
        for (piece in line.pieces) {
            when (piece) {
                is MathBlocks.Piece.Text -> out.appendMarkdown(piece.markdown)
                is MathBlocks.Piece.Math -> {
                    val math = MathRenderer.render(piece.latex, fontPx * MathRenderer.SCALE, color)
                    val start = out.length
                    if (math == null) {
                        // A formula the renderer cannot draw shows its source, like KaTeX's errors.
                        out.append("$${piece.latex}$")
                        out.setSpan(TypefaceSpan("monospace"), start, out.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                    } else {
                        out.append(LatexToPlain.plain(piece.latex) ?: piece.latex) // what copy and TalkBack read
                        out.setSpan(MathSpan(piece.latex, math), start, out.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
                    }
                }
            }
        }
        if (line.kind == MathBlocks.Line.Kind.HEADING) {
            out.setSpan(StyleSpan(Typeface.BOLD), lineStart, out.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
        }
    }
    if (cursor) {
        val start = out.length
        out.append(" ▍")
        out.setSpan(ForegroundColorSpan(cursorColor), start, out.length, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
    }
    return out
}

/**
 * A message: Markdown-ish text with `$inline$` formulas that wrap with the words, and
 * `$$display$$` formulas on their own lines (centred, scrolling sideways when too wide).
 * web: components/MathMarkdown.tsx; iOS: MathText.
 */
@Composable
fun MathText(
    text: String,
    modifier: Modifier = Modifier,
    cursor: Boolean = false,
    style: TextStyle = LocalTextStyle.current,
    color: Color = LocalContentColor.current,
    maxLines: Int = Int.MAX_VALUE,
    /** Paragraphs take the whole width (replies); false lets a bubble hug short text. */
    fill: Boolean = true,
) {
    val density = LocalDensity.current
    val fontPx = with(density) { style.fontSize.toPx() }
    val argb = color.toArgb()
    val cursorColor = MaterialTheme.colorScheme.onSurfaceVariant.toArgb()
    val blocks = remember(text) { MathBlocks.parse(MathNormalizer.normalize(text)) }
    Column(modifier, verticalArrangement = Arrangement.spacedBy(8.dp)) {
        blocks.forEachIndexed { index, block ->
            val last = cursor && index == blocks.lastIndex
            when (block) {
                is MathBlocks.Block.Paragraph -> {
                    val content = remember(block, fontPx, argb, last) { mathParagraph(block.lines, fontPx, argb, last, cursorColor) }
                    SpannedText(content, fontPx, argb, maxLines, if (fill) Modifier.fillMaxWidth() else Modifier)
                }
                is MathBlocks.Block.Display -> DisplayFormula(block.latex, fontPx * MathRenderer.SCALE * 1.05f, argb)
            }
        }
        if (cursor && blocks.lastOrNull() is MathBlocks.Block.Display) Text("▍", color = Color(cursorColor))
    }
}

/** A TextView, which draws spans (Compose text cannot place a bitmap on the baseline). */
@Composable
fun SpannedText(content: CharSequence, fontPx: Float, color: Int, maxLines: Int = Int.MAX_VALUE, modifier: Modifier = Modifier) {
    AndroidView(
        factory = { context ->
            TextView(context).apply {
                includeFontPadding = false
                // Compose semantics carry the text (TalkBack, tests), not the view.
                importantForAccessibility = View.IMPORTANT_FOR_ACCESSIBILITY_NO
                setLineSpacing(0f, 1.15f)
            }
        },
        update = { view ->
            view.setTextSize(android.util.TypedValue.COMPLEX_UNIT_PX, fontPx)
            view.setTextColor(color)
            view.maxLines = maxLines
            view.ellipsize = if (maxLines == Int.MAX_VALUE) null else android.text.TextUtils.TruncateAt.END
            view.text = content
        },
        modifier = modifier.semantics { text = AnnotatedString(content.toString()) },
    )
}

/** A display formula: centred when it fits, scrolling sideways when it does not. */
@Composable
fun DisplayFormula(latex: String, sizePx: Float, color: Int) {
    val math = remember(latex, sizePx, color) { MathRenderer.render(latex, sizePx, color, display = true) }
    if (math == null) {
        Text("$$$latex$$", style = MaterialTheme.typography.bodyMedium.copy(fontFamily = FontFamily.Monospace), color = MaterialTheme.colorScheme.onSurfaceVariant)
        return
    }
    val density = LocalDensity.current
    val width = with(density) { math.width.toDp() }
    val height = with(density) { math.height.toDp() }
    BoxWithConstraints(Modifier.fillMaxWidth().semantics { contentDescription = LatexToPlain.plain(latex) ?: latex }) {
        val available = maxWidth
        Box(Modifier.horizontalScroll(rememberScrollState())) {
            Box(Modifier.widthIn(min = available), contentAlignment = Alignment.Center) {
                Image(math.bitmap.asImageBitmap(), contentDescription = null, modifier = Modifier.requiredSize(width, height))
            }
        }
    }
}
