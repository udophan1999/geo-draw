package com.tvcsoft.mathmate.ui.composer

import android.net.Uri
import android.view.inputmethod.InputMethodManager
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.PickVisualMediaRequest
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.defaultMinSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.AddPhotoAlternate
import androidx.compose.material.icons.filled.Cancel
import androidx.compose.material.icons.filled.ChangeHistory
import androidx.compose.material.icons.filled.Functions
import androidx.compose.material.icons.filled.PhotoCamera
import androidx.compose.material.icons.filled.PhotoLibrary
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilledIconButton
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import com.tvcsoft.mathmate.ui.common.rememberUiScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.FileProvider
import com.tvcsoft.mathmate.core.SharedData
import com.tvcsoft.mathmate.core.chat.PreparedImage
import com.tvcsoft.mathmate.ui.common.ImagePrep
import com.tvcsoft.mathmate.ui.formula.FormulaSheet
import com.tvcsoft.mathmate.ui.theme.Haptics
import kotlinx.coroutines.launch
import java.io.File

/** Lets Compose drive the message box (insert a symbol or formula, clear it, focus it). */
class ComposerController {
    internal var view: MathEditText? = null
    var text by mutableStateOf("")
        internal set

    fun insert(snippet: String) { view?.insert(snippet); focus() }
    fun insertFormula(latex: String) { view?.insertFormula(latex); focus() }
    fun replaceFormula(position: Int, latex: String) { view?.replaceFormula(position, latex) }
    fun clear() { view?.clear() }
    fun load(message: String) { view?.load(message) }

    fun focus() {
        val view = view ?: return
        view.requestFocus()
        val keyboard = view.context.getSystemService(InputMethodManager::class.java)
        view.post { keyboard?.showSoftInput(view, 0) }
    }
}

/** A formula being written: new (`position` null) or a chip being edited. */
private data class FormulaEdit(val latex: String, val position: Int?)

/** The message box in Compose: grows with its text up to `maxHeight`, then scrolls. */
@Composable
fun ComposerField(
    controller: ComposerController,
    placeholder: String,
    modifier: Modifier = Modifier,
    initialText: String = "",
    autofocus: Boolean = false,
    maxLines: Int = 6,
    tag: String = "composer",
    onSubmit: () -> Unit = {},
    onImage: ((PreparedImage) -> Unit)? = null,
    onOpenFormula: (String, Int) -> Unit = { _, _ -> },
) {
    val textColor = MaterialTheme.colorScheme.onSurface.toArgb()
    val hintColor = MaterialTheme.colorScheme.onSurfaceVariant.toArgb()
    val chipColor = MaterialTheme.colorScheme.primary.copy(alpha = 0.12f).toArgb()
    val bodySize = MaterialTheme.typography.bodyLarge.fontSize
    AndroidView(
        factory = { context ->
            MathEditText(context).apply {
                controller.view = this
                setTextColor(textColor)
                formulaColor = textColor
                this.chipColor = chipColor
                setHintTextColor(hintColor)
                setBodyTextSize(bodySize.value * context.resources.displayMetrics.scaledDensity)
                onChange = { controller.text = it }
                load(initialText)
                if (autofocus) post { controller.focus() }
            }
        },
        update = { view ->
            controller.view = view
            view.hint = placeholder
            view.maxLines = maxLines
            view.onSubmit = onSubmit
            view.onImage = onImage?.let { handler -> { bitmap -> handler(ImagePrep.prepare(bitmap)) } }
            view.onOpenFormula = onOpenFormula
        },
        modifier = modifier.testTag(tag).semantics { contentDescription = controller.text },
    )
}

/**
 * The message box with its tools (web: chat/Composer.tsx; iOS: ChatComposer): formula chips,
 * the symbol bar, the formula editor, a photo of the problem (camera, library, paste) and
 * "Vẽ hình" when the conversation has no figure yet.
 */
@Composable
fun Composer(
    placeholder: String,
    busy: Boolean,
    onDraw: (() -> Unit)?,
    onSend: suspend (String, PreparedImage?) -> Boolean,
) {
    val controller = remember { ComposerController() }
    var image by remember { mutableStateOf<PreparedImage?>(null) }
    var symbols by remember { mutableStateOf(false) }
    var formula by remember { mutableStateOf<FormulaEdit?>(null) }
    var submitting by remember { mutableStateOf(false) }
    var attachMenu by remember { mutableStateOf(false) }
    val scope = rememberUiScope()
    val context = LocalContext.current
    val canSend = !busy && !submitting && (controller.text.isNotBlank() || image != null)

    fun submit() {
        if (!canSend) return
        submitting = true
        scope.launch {
            if (onSend(controller.text.trim(), image)) {
                controller.clear()
                image = null
            }
            submitting = false
        }
    }

    val pickPhoto = rememberLauncherForActivityResult(ActivityResultContracts.PickVisualMedia()) { uri: Uri? ->
        if (uri != null) scope.launch { image = ImagePrep.prepare(context, uri) }
    }
    var cameraFile by remember { mutableStateOf<Uri?>(null) }
    val takePhoto = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { taken ->
        val uri = cameraFile
        if (taken && uri != null) scope.launch { image = ImagePrep.prepare(context, uri) }
    }

    Surface(
        shape = RoundedCornerShape(24.dp),
        color = MaterialTheme.colorScheme.surfaceContainer,
        tonalElevation = 2.dp,
        shadowElevation = 2.dp,
    ) {
        Column(Modifier.padding(start = 14.dp, end = 8.dp, top = 6.dp, bottom = 6.dp)) {
            image?.let { attached -> Attachment(attached) { image = null } }
            AnimatedVisibility(symbols) { SymbolBar { controller.insert(it) } }
            ComposerField(
                controller, placeholder,
                modifier = Modifier.fillMaxWidth().heightIn(min = 44.dp),
                onSubmit = ::submit,
                onImage = { image = it },
                onOpenFormula = { latex, position -> formula = FormulaEdit(latex, position) },
            )
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box {
                    IconButton(onClick = { attachMenu = true }, modifier = Modifier.testTag("attach")) {
                        Icon(Icons.Filled.AddPhotoAlternate, contentDescription = "Đính kèm ảnh đề", tint = MaterialTheme.colorScheme.primary)
                    }
                    DropdownMenu(expanded = attachMenu, onDismissRequest = { attachMenu = false }) {
                        DropdownMenuItem(
                            text = { Text("Chụp đề") },
                            leadingIcon = { Icon(Icons.Filled.PhotoCamera, null) },
                            onClick = {
                                attachMenu = false
                                val dir = File(context.cacheDir, "photos").apply { mkdirs() }
                                val uri = FileProvider.getUriForFile(context, "${context.packageName}.files", File(dir, "de-bai.jpg"))
                                cameraFile = uri
                                takePhoto.launch(uri)
                            },
                        )
                        DropdownMenuItem(
                            text = { Text("Thư viện ảnh") },
                            leadingIcon = { Icon(Icons.Filled.PhotoLibrary, null) },
                            onClick = {
                                attachMenu = false
                                pickPhoto.launch(PickVisualMediaRequest(ActivityResultContracts.PickVisualMedia.ImageOnly))
                            },
                        )
                    }
                }
                // Ω, as on the web's button.
                Box(
                    Modifier
                        .size(36.dp)
                        .clip(CircleShape)
                        .background(if (symbols) MaterialTheme.colorScheme.primary else androidx.compose.ui.graphics.Color.Transparent),
                    contentAlignment = Alignment.Center,
                ) {
                    TextButton(
                        onClick = { symbols = !symbols },
                        modifier = Modifier.testTag("toggleSymbols").semantics { contentDescription = "Ký hiệu toán" },
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(0.dp),
                    ) {
                        Text("Ω", fontSize = 20.sp, fontWeight = FontWeight.Medium, color = if (symbols) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.primary)
                    }
                }
                IconButton(onClick = { formula = FormulaEdit("", null) }, modifier = Modifier.testTag("openFormula")) {
                    Icon(Icons.Filled.Functions, contentDescription = "Nhập công thức", tint = MaterialTheme.colorScheme.primary)
                }
                Spacer(Modifier.weight(1f))
                if (onDraw != null) {
                    TextButton(onClick = onDraw, modifier = Modifier.testTag("drawFigure")) {
                        Icon(Icons.Filled.ChangeHistory, null, modifier = Modifier.size(18.dp))
                        Spacer(Modifier.size(4.dp))
                        Text("Vẽ hình")
                    }
                }
                FilledIconButton(onClick = ::submit, enabled = canSend, modifier = Modifier.testTag("send")) {
                    if (submitting) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                    else Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Gửi")
                }
            }
        }
    }

    formula?.let { edit ->
        FormulaSheet(
            initialLatex = edit.latex,
            editingExisting = edit.position != null,
            onDismiss = { formula = null },
            onDone = { latex ->
                formula = null
                val position = edit.position
                if (position != null) controller.replaceFormula(position, latex) else controller.insertFormula(latex)
            },
        )
    }
}

@Composable
private fun Attachment(image: PreparedImage, onRemove: () -> Unit) {
    val preview = remember(image) { ImagePrep.preview(image) }
    Box(Modifier.padding(top = 6.dp, bottom = 4.dp).testTag("attachedImage")) {
        preview?.let {
            Image(
                it.asImageBitmap(), contentDescription = "Ảnh đề",
                contentScale = ContentScale.Crop,
                modifier = Modifier.size(72.dp).clip(RoundedCornerShape(10.dp)),
            )
        }
        IconButton(onClick = onRemove, modifier = Modifier.align(Alignment.TopEnd).size(28.dp)) {
            Icon(Icons.Filled.Cancel, contentDescription = "Bỏ ảnh", tint = MaterialTheme.colorScheme.onSurface)
        }
    }
}

/** Common symbols as Unicode, one tap each (web: chat/MathInput.tsx SymbolBar; shared/symbols.json). */
@Composable
fun SymbolBar(onInsert: (String) -> Unit) {
    val context = LocalContext.current
    Row(
        Modifier.horizontalScroll(rememberScrollState()).padding(vertical = 4.dp).testTag("symbolBar"),
        horizontalArrangement = Arrangement.spacedBy(6.dp),
    ) {
        for (symbol in SharedData.symbols) {
            Surface(
                onClick = {
                    Haptics.tick(context)
                    onInsert(symbol.symbol)
                },
                shape = RoundedCornerShape(8.dp),
                color = MaterialTheme.colorScheme.surfaceContainerHigh,
                modifier = Modifier.defaultMinSize(36.dp, 36.dp).semantics { contentDescription = symbol.name },
            ) {
                Box(contentAlignment = Alignment.Center, modifier = Modifier.defaultMinSize(36.dp, 36.dp)) {
                    Text(symbol.symbol, style = MaterialTheme.typography.bodyLarge)
                }
            }
        }
    }
}
