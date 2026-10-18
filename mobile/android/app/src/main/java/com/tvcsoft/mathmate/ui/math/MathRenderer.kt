package com.tvcsoft.mathmate.ui.math

import android.graphics.Bitmap
import android.graphics.Canvas
import android.util.LruCache
import com.agog.mathdisplay.MTFontManager
import com.agog.mathdisplay.parse.MTLineStyle
import com.agog.mathdisplay.parse.MTMathList
import com.agog.mathdisplay.parse.MTMathListBuilder
import com.agog.mathdisplay.parse.MTParseError
import com.agog.mathdisplay.parse.MTParseErrors
import com.agog.mathdisplay.render.CGPoint
import com.agog.mathdisplay.render.MTFont
import com.agog.mathdisplay.render.MTMathListDisplay
import com.agog.mathdisplay.render.MTTypesetter
import kotlin.math.ceil

/**
 * A typeset formula as a bitmap, with the baseline measurements needed to sit it in a line of
 * text (pixels): `ascent` above the baseline, `descent` below it. The bitmap has `PAD` pixels of
 * room on every side, so glyphs that overhang their advance are not clipped.
 */
class RenderedMath(val bitmap: Bitmap, val ascent: Float, val descent: Float) {
    val width get() = bitmap.width
    val height get() = bitmap.height

    companion object {
        const val PAD = 2
    }
}

/**
 * Typesets LaTeX with the AndroidMath fork (docs/mobile-android-plan.md §4) into cached bitmaps;
 * the iOS app's MathRenderer does the same with SwiftMath. FreeType is not thread-safe, so
 * everything here runs on the main thread.
 */
object MathRenderer {
    /**
     * TeX Gyre Termes is Times-like (as in Vietnamese textbooks) and has every Vietnamese letter;
     * formulas are drawn a little larger than the body text, whose x-height is taller.
     */
    const val SCALE = 1.08f

    private val cache = object : LruCache<String, Entry>(24 * 1024 * 1024) {
        override fun sizeOf(key: String, value: Entry) = value.math?.bitmap?.allocationByteCount ?: 64
    }

    /** Wraps a nullable result, so formulas that cannot be drawn are remembered too. */
    private class Entry(val math: RenderedMath?)

    fun font(sizePx: Float): MTFont? = MTFontManager.termesFontWithSize(sizePx)

    /** Commands the fork does not know, written in ones it does. */
    fun prepare(latex: String): String =
        latex.replace(Regex("""\\operatorname\{([^{}]*)\}"""), """\\mathrm{$1}""")

    /** The parsed formula, or null when the fork cannot read it. */
    fun parse(latex: String): MTMathList? {
        val error = MTParseError()
        val list = MTMathListBuilder.buildFromString(prepare(latex), error)
        return if (error.errorcode == MTParseErrors.ErrorNone) list else null
    }

    /** The display list (y up from the baseline at 0), for drawing and hit-testing. */
    fun typeset(list: MTMathList, sizePx: Float, display: Boolean): MTMathListDisplay? {
        val font = font(sizePx) ?: return null
        return try {
            MTTypesetter.createLineForMathList(list, font, if (display) MTLineStyle.KMTLineStyleDisplay else MTLineStyle.KMTLineStyleText)
        } catch (_: Exception) {
            null
        }
    }

    /** null when the formula cannot be drawn; callers then show the LaTeX source. */
    fun render(latex: String, sizePx: Float, color: Int, display: Boolean = false): RenderedMath? {
        val key = "${if (display) 'D' else 'T'}|$sizePx|$color|$latex"
        cache.get(key)?.let { return it.math }
        val rendered = try {
            parse(latex)?.let { typeset(it, sizePx, display) }?.let { draw(it, color) }
        } catch (_: Exception) {
            null // a glyph the font lacks, or a construct the typesetter cannot lay out
        }
        cache.put(key, Entry(rendered))
        return rendered
    }

    /** Draws a display list into a bitmap: the baseline at `PAD + ascent` from the top. */
    fun draw(line: MTMathListDisplay, color: Int): RenderedMath? {
        if (line.width <= 0f) return null
        val pad = RenderedMath.PAD
        val width = ceil(line.width).toInt() + pad * 2
        val height = ceil(line.ascent + line.descent).toInt() + pad * 2
        val bitmap = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
        val canvas = Canvas(bitmap)
        line.textColor = color
        line.position = CGPoint(pad.toFloat(), pad + line.descent)
        canvas.translate(0f, height.toFloat())
        canvas.scale(1f, -1f) // the display draws with y going up
        line.draw(canvas)
        return RenderedMath(bitmap, line.ascent, line.descent)
    }
}
