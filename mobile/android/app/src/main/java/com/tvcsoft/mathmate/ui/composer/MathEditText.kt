package com.tvcsoft.mathmate.ui.composer

import android.annotation.SuppressLint
import android.content.ClipboardManager
import android.content.Context
import android.graphics.Bitmap
import android.graphics.ImageDecoder
import android.os.Build
import android.provider.MediaStore
import android.text.Editable
import android.text.InputType
import android.text.Spannable
import android.text.SpannableStringBuilder
import android.text.Spanned
import android.text.TextWatcher
import android.util.TypedValue
import android.view.Gravity
import android.view.KeyEvent
import android.view.MotionEvent
import android.view.inputmethod.BaseInputConnection
import android.widget.EditText
import com.tvcsoft.mathmate.core.math.LatexToPlain
import com.tvcsoft.mathmate.core.math.MessageTextCodec
import com.tvcsoft.mathmate.core.math.MessageTextCodec.Piece
import com.tvcsoft.mathmate.ui.math.MathRenderer
import com.tvcsoft.mathmate.ui.math.MathSpan

/** The character a formula chip stands on; the LaTeX lives in its MathSpan. */
const val CHIP = '￼'

/**
 * The message box: text with formula chips (web: components/chat/useMathEditor.tsx; iOS:
 * MathTextView).
 * - `$…$` typed or pasted becomes a chip; one Backspace right after gives the source back.
 * - A tap on a chip opens it in the formula editor.
 * - A pasted image becomes the attachment.
 * - Hardware keyboard: Enter sends, Shift+Enter breaks the line.
 */
@SuppressLint("AppCompatCustomView")
class MathEditText(context: Context) : EditText(context) {
    var onChange: ((String) -> Unit)? = null
    var onSubmit: (() -> Unit)? = null
    var onImage: ((Bitmap) -> Unit)? = null
    /** A chip was tapped: its LaTeX and its position in the text. */
    var onOpenFormula: ((String, Int) -> Unit)? = null

    /** The chip that `$…$` just became: one Backspace right away gives the source back. */
    private var justConverted: Pair<Int, String>? = null
    private var restoring: Pair<Int, String>? = null
    private var deleting = false
    private var updating = false

    var chipColor: Int = 0x1F2563EB
    var formulaColor: Int = currentTextColor

    init {
        background = null
        gravity = Gravity.TOP or Gravity.START
        setPadding(0, 16, 0, 16)
        inputType = InputType.TYPE_CLASS_TEXT or InputType.TYPE_TEXT_FLAG_MULTI_LINE or InputType.TYPE_TEXT_FLAG_CAP_SENTENCES
        isVerticalScrollBarEnabled = true
        addTextChangedListener(object : TextWatcher {
            override fun beforeTextChanged(text: CharSequence, start: Int, count: Int, after: Int) {
                if (updating) return
                deleting = after < count
                val converted = justConverted
                restoring = if (converted != null && count == 1 && after == 0 && start == converted.first) converted else null
                if (after > 0 || count > 0) justConverted = null
            }

            override fun onTextChanged(text: CharSequence, start: Int, before: Int, count: Int) {}

            override fun afterTextChanged(text: Editable) {
                if (updating) return
                updating = true
                try {
                    restoring?.let { (location, latex) ->
                        // Backspace right after a conversion: the chip becomes `$latex$` text again.
                        val source = "$$latex$"
                        text.insert(location, source)
                        setSelection(location + source.length)
                    } ?: run {
                        if (!deleting && BaseInputConnection.getComposingSpanStart(text) < 0) applyTypedRule(text)
                    }
                    restoring = null
                } finally {
                    updating = false
                }
                changed()
            }
        })
    }

    val fontPx: Float get() = textSize

    // Content

    /** The message: text with `$latex$` for every chip. */
    val messageText: String get() = MessageTextCodec.messageText(pieces(text))

    val isEmptyText: Boolean get() = text.isNullOrEmpty()

    fun chip(latex: String): CharSequence {
        val out = SpannableStringBuilder(CHIP.toString())
        val math = MathRenderer.render(latex, fontPx * MathRenderer.SCALE, formulaColor)
        if (math != null) {
            out.setSpan(MathSpan(latex, math, chipColor), 0, 1, Spanned.SPAN_EXCLUSIVE_EXCLUSIVE)
            return out
        }
        // A formula the renderer cannot draw stays as its source, like KaTeX's errors on the web.
        return "$$latex$"
    }

    private fun content(pieces: List<Piece>): CharSequence {
        val out = SpannableStringBuilder()
        for (piece in pieces) {
            when (piece) {
                is Piece.Text -> out.append(piece.text)
                is Piece.Formula -> out.append(chip(piece.latex))
            }
        }
        return out
    }

    /** Load a stored message (editing it): `$latex$` back to chips. */
    fun load(message: String) {
        replaceAll(content(MessageTextCodec.piecesOfMessage(message)))
        setSelection(text.length)
    }

    fun clear() = replaceAll("")

    private fun replaceAll(content: CharSequence) {
        updating = true
        setText(content)
        updating = false
        justConverted = null
        changed()
    }

    /** Put text at the caret (the symbol bar) and keep typing after it. */
    fun insert(snippet: CharSequence) {
        val start = selectionStart.coerceAtLeast(0)
        val end = selectionEnd.coerceAtLeast(0)
        updating = true
        text.replace(minOf(start, end), maxOf(start, end), snippet)
        updating = false
        justConverted = null
        setSelection(minOf(start, end) + snippet.length)
        changed()
    }

    /**
     * A formula from the editor: plain Unicode when it can be (`BC²`), else a chip, kept apart
     * from the words around it by spaces.
     */
    fun insertFormula(latex: String) {
        val start = minOf(selectionStart, selectionEnd).coerceAtLeast(0)
        val end = maxOf(selectionStart, selectionEnd).coerceAtLeast(0)
        val before = if (start > 0) text[start - 1] else null
        val after = if (end < text.length) text[end] else null
        val out = SpannableStringBuilder()
        if (before != null && !before.isWhitespace()) out.append(' ')
        out.append(LatexToPlain.plain(latex) ?: chip(latex))
        if (after == null || !after.isWhitespace()) out.append(' ')
        setSelection(start, end)
        insert(out)
    }

    /** An edited chip (from the formula editor). */
    fun replaceFormula(position: Int, latex: String) {
        if (position >= text.length || text[position] != CHIP) return
        setSelection(position, position + 1)
        insert(chip(latex))
    }

    private fun changed() {
        contentDescription = messageText
        onChange?.invoke(messageText)
    }

    // Typing rules

    /** After typing: a `$…$` just closed before the caret becomes a chip. */
    private fun applyTypedRule(text: Editable) {
        val caret = selectionStart
        if (caret <= 0) return
        val lineStart = text.lastIndexOf('\n', caret - 1) + 1
        val before = text.substring(lineStart, caret)
        val match = MessageTextCodec.typedFormula.find(before) ?: return
        val start = lineStart + match.groups[1]!!.range.last + 1
        val latex = match.groupValues[2]
        val chip = chip(latex)
        if (chip !is Spannable) return
        text.replace(start, caret, chip)
        setSelection(start + 1)
        justConverted = start to latex
    }

    // Taps on chips

    @SuppressLint("ClickableViewAccessibility")
    override fun onTouchEvent(event: MotionEvent): Boolean {
        if (event.action == MotionEvent.ACTION_UP && layout != null) {
            chipAt(event.x, event.y)?.let { (position, span) ->
                onOpenFormula?.invoke(span.latex, position)
                return true
            }
        }
        return super.onTouchEvent(event)
    }

    private fun chipAt(x: Float, y: Float): Pair<Int, MathSpan>? {
        val layout = layout ?: return null
        val localX = x - totalPaddingLeft + scrollX
        val localY = (y - totalPaddingTop + scrollY).toInt()
        val line = layout.getLineForVertical(localY)
        val offset = layout.getOffsetForHorizontal(line, localX)
        for (candidate in listOf(offset, offset - 1)) {
            if (candidate < 0 || candidate >= text.length || text[candidate] != CHIP) continue
            val span = text.getSpans(candidate, candidate + 1, MathSpan::class.java).firstOrNull() ?: continue
            val left = layout.getPrimaryHorizontal(candidate)
            val right = if (candidate + 1 <= layout.getLineEnd(line)) layout.getPrimaryHorizontal(candidate + 1) else left
            if (localX >= minOf(left, right) && localX <= maxOf(left, right) + 1) return candidate to span
        }
        return null
    }

    // Paste

    override fun onTextContextMenuItem(id: Int): Boolean {
        if (id == android.R.id.paste || id == android.R.id.pasteAsPlainText) {
            val clipboard = context.getSystemService(Context.CLIPBOARD_SERVICE) as ClipboardManager
            val item = clipboard.primaryClip?.takeIf { it.itemCount > 0 }?.getItemAt(0)
            val uri = item?.uri
            if (uri != null && onImage != null && context.contentResolver.getType(uri)?.startsWith("image/") == true) {
                imageFrom(uri)?.let { onImage?.invoke(it) }
                return true
            }
            val pasted = item?.coerceToText(context)?.toString()
            if (pasted != null && pasted.contains('$')) {
                insert(content(MessageTextCodec.piecesOfPasted(pasted)))
                return true
            }
        }
        return super.onTextContextMenuItem(id)
    }

    private fun imageFrom(uri: android.net.Uri): Bitmap? = try {
        if (Build.VERSION.SDK_INT >= 28) {
            ImageDecoder.decodeBitmap(ImageDecoder.createSource(context.contentResolver, uri)) { decoder, _, _ ->
                decoder.allocator = ImageDecoder.ALLOCATOR_SOFTWARE
            }
        } else {
            @Suppress("DEPRECATION")
            MediaStore.Images.Media.getBitmap(context.contentResolver, uri)
        }
    } catch (_: Exception) {
        null
    }

    // Hardware keyboard

    override fun onKeyDown(keyCode: Int, event: KeyEvent): Boolean {
        val physical = event.device?.isVirtual == false
        if (physical && (keyCode == KeyEvent.KEYCODE_ENTER || keyCode == KeyEvent.KEYCODE_NUMPAD_ENTER)) {
            if (event.isShiftPressed) {
                insert("\n")
            } else if (BaseInputConnection.getComposingSpanStart(text) < 0) {
                // A Vietnamese input method may still be composing: let Enter finish the word.
                onSubmit?.invoke()
            } else {
                return super.onKeyDown(keyCode, event)
            }
            return true
        }
        return super.onKeyDown(keyCode, event)
    }

    fun setBodyTextSize(px: Float) = setTextSize(TypedValue.COMPLEX_UNIT_PX, px)

    companion object {
        /** The box's content as pieces: chips are formulas. */
        fun pieces(content: CharSequence?): List<Piece> {
            if (content == null) return emptyList()
            val spanned = content as? Spanned
            val out = mutableListOf<Piece>()
            val buffer = StringBuilder()
            for (index in content.indices) {
                val span = if (content[index] == CHIP) spanned?.getSpans(index, index + 1, MathSpan::class.java)?.firstOrNull() else null
                if (span != null) {
                    if (buffer.isNotEmpty()) out.add(Piece.Text(buffer.toString())).also { buffer.clear() }
                    out.add(Piece.Formula(span.latex))
                } else if (content[index] != CHIP) {
                    buffer.append(content[index])
                }
            }
            if (buffer.isNotEmpty()) out.add(Piece.Text(buffer.toString()))
            return out
        }
    }
}
