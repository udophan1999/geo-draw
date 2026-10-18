package com.tvcsoft.mathmate.ui.formula

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.BoxWithConstraints
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.focus.FocusRequester
import androidx.compose.ui.focus.focusRequester
import androidx.compose.ui.graphics.toArgb
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontFamily
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import com.tvcsoft.mathmate.ui.math.DisplayFormula
import com.tvcsoft.mathmate.ui.math.MathRenderer

/**
 * Writing a formula (web: chat/MathInput.tsx FormulaDialog with MathLive; iOS: FormulaSheet):
 * visual by default, with the math keyboard and the gallery; "Sửa LaTeX" for what the visual
 * editor cannot open (tables such as `cases`) or for typing LaTeX directly.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun FormulaSheet(initialLatex: String, editingExisting: Boolean, onDismiss: () -> Unit, onDone: (String) -> Unit) {
    var model by remember { mutableStateOf(FormulaEditorModel.create(initialLatex)) }
    var latex by remember { mutableStateOf(initialLatex) }
    // A table (cases…) opens as LaTeX.
    var rawMode by remember { mutableStateOf(model == null) }
    val visual = model
    val current = (if (rawMode || visual == null) latex else visual.latex).trim()

    Dialog(onDismissRequest = onDismiss, properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false)) {
        Scaffold(
            topBar = {
                TopAppBar(
                    title = { Text(if (editingExisting) "Sửa công thức" else "Công thức") },
                    navigationIcon = { IconButton(onClick = onDismiss) { Icon(Icons.Filled.Close, contentDescription = "Hủy") } },
                    actions = {
                        TextButton(
                            onClick = {
                                if (rawMode) {
                                    FormulaEditorModel.create(latex)?.let { model = it; rawMode = false }
                                } else {
                                    latex = model?.latex ?: latex
                                    rawMode = true
                                }
                            },
                            enabled = !rawMode || FormulaEditorModel.create(latex) != null,
                            modifier = Modifier.testTag("toggleLatex"),
                        ) { Text(if (rawMode) "Bảng phím" else "Sửa LaTeX") }
                        TextButton(
                            onClick = { onDone(current) },
                            enabled = current.isNotEmpty(),
                            modifier = Modifier.testTag("insertFormula"),
                        ) { Text(if (editingExisting) "Lưu" else "Chèn") }
                    },
                )
            },
            modifier = Modifier.fillMaxSize(),
        ) { padding ->
            Column(Modifier.padding(padding).fillMaxSize().navigationBarsPadding()) {
                if (rawMode || visual == null) {
                    RawLatexEditor(latex) { latex = it }
                } else {
                    BoxWithConstraints(
                        Modifier
                            .weight(1f)
                            .fillMaxWidth()
                            .padding(16.dp),
                    ) {
                        val width = maxWidth
                        val height = maxHeight
                        Surface(shape = RoundedCornerShape(16.dp), color = MaterialTheme.colorScheme.surfaceContainerLow, modifier = Modifier.fillMaxSize()) {
                            Box(Modifier.horizontalScroll(rememberScrollState(), reverseScrolling = false)) {
                                FormulaCanvas(visual, minWidth = width, height = height)
                            }
                        }
                    }
                    MathKeyboard(visual)
                }
            }
        }
    }
}

/** LaTeX with a live preview, and the gallery adding templates to it. */
@Composable
private fun RawLatexEditor(latex: String, onChange: (String) -> Unit) {
    val focus = remember { FocusRequester() }
    val density = LocalDensity.current
    val color = MaterialTheme.colorScheme.onSurface.toArgb()
    LaunchedEffect(Unit) { focus.requestFocus() }
    Column(Modifier.fillMaxSize().imePadding()) {
        Surface(color = MaterialTheme.colorScheme.surfaceContainerLow, modifier = Modifier.fillMaxWidth().heightIn(min = 90.dp)) {
            Box(Modifier.padding(vertical = 12.dp), contentAlignment = Alignment.Center) {
                val trimmed = latex.trim()
                when {
                    trimmed.isEmpty() -> Text("Gõ LaTeX hoặc chọn một mẫu bên dưới", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    MathRenderer.render(trimmed, with(density) { 26.dp.toPx() }, color, display = true) != null ->
                        DisplayFormula(trimmed, with(density) { 26.dp.toPx() }, color)
                    else -> Text("Công thức chưa đúng cú pháp", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.error)
                }
            }
        }
        OutlinedTextField(
            value = latex,
            onValueChange = onChange,
            placeholder = { Text("Ví dụ: \\frac{1}{2} hoặc x^2") },
            textStyle = MaterialTheme.typography.bodyLarge.copy(fontFamily = FontFamily.Monospace),
            keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.None, autoCorrectEnabled = false),
            maxLines = 4,
            modifier = Modifier.fillMaxWidth().padding(12.dp).focusRequester(focus).testTag("latexField"),
        )
        HorizontalDivider()
        Box(Modifier.weight(1f).padding(12.dp)) {
            TemplateGallery { template ->
                // Slots become empty groups, and #@ takes what was written so far.
                val current = latex.trim()
                onChange(
                    if (template.contains("#@")) template.replace("#@", current).replace("#?", "")
                    else current + template.replace("#?", ""),
                )
            }
        }
    }
}
