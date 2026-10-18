package com.tvcsoft.mathmate

import android.graphics.Bitmap
import android.graphics.Canvas
import android.graphics.Color
import android.graphics.Paint
import androidx.test.ext.junit.runners.AndroidJUnit4
import androidx.test.platform.app.InstrumentationRegistry
import com.tvcsoft.mathmate.core.SharedData
import com.tvcsoft.mathmate.ui.math.MathRenderer
import org.junit.Assert.assertEquals
import org.junit.Assert.assertNotNull
import org.junit.Test
import org.junit.runner.RunWith
import java.io.File

/**
 * Every template of the formula gallery and the notation the tutor writes can be drawn. Also
 * writes a contact sheet to the app's files (`adb pull` it to look at the formulas).
 */
@RunWith(AndroidJUnit4::class)
class MathRenderTest {
    private val samples = listOf(
        "\\widehat{ABC} = 90^\\circ", "\\widehat{A_1}", "\\overrightarrow{AB} + \\overrightarrow{BC} = \\overrightarrow{AC}",
        "\\overset{\\frown}{AB}", "\\overset{\\frown}{AmB}", "\\triangle ABC \\backsim \\triangle DEF",
        "\\dfrac{1}{2} + \\frac{1}{3}", "x = \\frac{-b \\pm \\sqrt{\\Delta}}{2a}", "\\begin{cases} x + y = 3 \\\\ x - y = 1 \\end{cases}",
        "\\lim_{x \\to 0} \\frac{\\sin x}{x} = 1", "\\int_0^1 x^2\\,dx", "\\sum_{i=1}^{n} i", "\\left\\{ x \\in \\mathbb{R} \\mid x > 0 \\right\\}",
        "\\text{Vì } AB \\parallel CD \\text{ nên } \\widehat{A} = \\widehat{D} \\text{ (so le trong)}", "\\varnothing", "x \\leqslant 2 \\implies y \\geqslant 3",
        "AB \\perp CD", "\\sqrt[3]{x^2 + 1}", "\\overline{AB}", "\\vec{u}", "\\operatorname{tg} x",
        "f'(x) = 2x", "x ≥ 0,\\ ∠A = 90°", "\\text{Đặt } t = x^2 \\text{ (điều kiện } t \\ge 0)",
        "\\widehat{ABCD} + \\overrightarrow{MN}",
    )

    @Test
    fun everyTemplateAndTutorFormulaIsDrawn() {
        val context = InstrumentationRegistry.getInstrumentation().targetContext
        InstrumentationRegistry.getInstrumentation().runOnMainSync {
            val templates = SharedData.formulaGroups.flatMap { group ->
                group.items.map { it.latex.replace("#?", "\\square ").replace("#@", "\\square ") }
            }
            assertEquals(85, templates.size)
            val all = templates + samples
            val failed = all.filter { MathRenderer.render(it, 48f, Color.BLACK) == null }
            assertEquals("cannot draw: $failed", emptyList<String>(), failed)

            // The contact sheet: one formula per row, its source in small print beside it.
            val rendered = all.map { it to MathRenderer.render(it, 48f, Color.BLACK)!! }
            val width = 1400
            val height = rendered.sumOf { maxOf(it.second.height, 30) + 16 }
            val sheet = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888)
            val canvas = Canvas(sheet)
            canvas.drawColor(Color.WHITE)
            val label = Paint(Paint.ANTI_ALIAS_FLAG).apply { textSize = 18f; color = Color.GRAY }
            var y = 8f
            for ((latex, math) in rendered) {
                canvas.drawBitmap(math.bitmap, 16f, y, null)
                canvas.drawText(latex.take(70), 720f, y + 24f, label)
                y += maxOf(math.height, 30) + 16
            }
            val file = File(context.getExternalFilesDir(null), "formulas.png")
            file.outputStream().use { sheet.compress(Bitmap.CompressFormat.PNG, 100, it) }
            assertNotNull(file)
        }
    }
}
