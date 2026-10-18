package com.tvcsoft.mathmate.ui.formula

import androidx.compose.foundation.Canvas
import androidx.compose.foundation.focusable
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.drawscope.drawIntoCanvas
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.input.key.Key
import androidx.compose.ui.input.key.KeyEventType
import androidx.compose.ui.input.key.key
import androidx.compose.ui.input.key.onKeyEvent
import androidx.compose.ui.input.key.type
import androidx.compose.ui.input.key.utf16CodePoint
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.semantics.stateDescription
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import com.agog.mathdisplay.edit.MTMathEditor
import com.agog.mathdisplay.edit.MTMathListIndex
import com.agog.mathdisplay.edit.atomAt
import com.agog.mathdisplay.edit.caretPosition
import com.agog.mathdisplay.edit.closestIndex
import com.agog.mathdisplay.parse.MTMathAtomType
import com.agog.mathdisplay.render.CGPoint
import com.agog.mathdisplay.render.MTMathListDisplay
import com.tvcsoft.mathmate.ui.math.MathRenderer

/** The formula being edited, shared by the canvas that draws it and the math keyboard (iOS: FormulaEditorModel). */
class FormulaEditorModel private constructor(private val editor: MTMathEditor) {
    /** Bumped on every change, so the canvas draws again. */
    var version by mutableIntStateOf(0)
        private set

    // Read through `version`: the editor is not observable.
    val latex: String get() = version.let { editor.latex }
    val isEmpty: Boolean get() = version.let { editor.isEmpty }
    val mathList get() = editor.mathList
    val caret: MTMathListIndex get() = editor.caret

    fun key(input: String) = changed { editor.insert(input) }
    fun template(latex: String) = changed { editor.insertTemplate(latex) }
    fun backspace() = changed { editor.deleteBackward() }
    fun left() = changed { editor.moveLeft() }
    fun right() = changed { editor.moveRight() }
    fun moveCaret(index: MTMathListIndex) = changed { editor.moveCaret(index) }

    private inline fun changed(action: () -> Unit) {
        action()
        version += 1
    }

    companion object {
        fun create(latex: String): FormulaEditorModel? = MTMathEditor.create(latex)?.let(::FormulaEditorModel)
    }
}

/**
 * Draws the formula with the caret; a tap moves the caret there (iOS: FormulaCanvas). A hardware
 * keyboard types into it too (letters, digits, Backspace, ← →); the on-screen keyboard is
 * MathKeyboard, not the system one.
 */
@Composable
fun FormulaCanvas(model: FormulaEditorModel, minWidth: Dp, height: Dp, modifier: Modifier = Modifier) {
    val density = LocalDensity.current
    val fontPx = with(density) { 30.dp.toPx() }
    val inset = with(density) { 16.dp.toPx() }
    val color = MaterialTheme.colorScheme.onSurface.toArgb()
    val caretColor = MaterialTheme.colorScheme.primary
    val version = model.version
    val display: MTMathListDisplay? = remember(version, fontPx) { MathRenderer.typeset(model.mathList, fontPx, display = true) }
    val focus = remember { FocusRequester() }
    val contentWidth = with(density) { ((display?.width ?: 0f) + inset * 2).toDp() }
    val heightPx = with(density) { height.toPx() }

    fun origin(): Offset {
        val ascent = display?.ascent ?: (fontPx * 0.8f)
        val descent = display?.descent ?: (fontPx * 0.2f)
        return Offset(inset, (heightPx + ascent - descent) / 2)
    }

    Box(
        modifier
            .width(maxOf(minWidth, contentWidth))
            .height(height)
            .semantics {
                contentDescription = "Công thức"
                stateDescription = model.latex
            }
            .testTag("formulaEditor")
            .focusRequester(focus)
            .focusable()
            .onKeyEvent { event ->
                if (event.type != KeyEventType.KeyDown) return@onKeyEvent false
                when (event.key) {
                    Key.Backspace -> model.backspace()
                    Key.DirectionLeft -> model.left()
                    Key.DirectionRight -> model.right()
                    else -> {
                        val code = event.utf16CodePoint
                        if (code <= 0x20 || code == 0x7F) return@onKeyEvent false
                        model.key(String(Character.toChars(code)))
                    }
                }
                true
            }
            .pointerInput(display) {
                detectTapGestures { tap ->
                    focus.requestFocus()
                    val line = display ?: return@detectTapGestures
                    val o = origin()
                    line.position = CGPoint()
                    line.closestIndex(CGPoint(tap.x - o.x, o.y - tap.y))?.let(model::moveCaret)
                }
            },
    ) {
        Canvas(Modifier.width(maxOf(minWidth, contentWidth)).height(height)) {
            val o = origin()
            val line = display
            if (line != null) {
                drawIntoCanvas { canvas ->
                    val native = canvas.nativeCanvas
                    native.save()
                    native.translate(0f, size.height)
                    native.scale(1f, -1f) // the display draws with y going up
                    line.textColor = color
                    line.position = CGPoint(o.x, size.height - o.y)
                    line.draw(native)
                    native.restore()
                }
                line.position = CGPoint() // hit-testing works from the baseline at zero
            }
            // On an empty slot the black square is the caret: no line.
            val onSlot = model.mathList.atomAt(model.caret)?.type == MTMathAtomType.KMTMathAtomPlaceholder
            if (!onSlot) {
                val caret = line?.caretPosition(model.caret) ?: CGPoint(line?.width ?: 0f, 0f)
                val x = o.x + caret.x
                val top = o.y - caret.y - fontPx * 0.72f
                drawLine(caretColor, Offset(x, top), Offset(x, top + fontPx * 0.95f), strokeWidth = 2.dp.toPx())
            }
        }
        if (model.isEmpty) {
            Text(
                "Gõ công thức bằng bàn phím bên dưới",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant,
                modifier = Modifier.align(androidx.compose.ui.Alignment.CenterStart).padding(start = 28.dp),
            )
        }
    }
}
