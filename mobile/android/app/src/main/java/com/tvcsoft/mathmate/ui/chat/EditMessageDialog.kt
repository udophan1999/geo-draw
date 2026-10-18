package com.tvcsoft.mathmate.ui.chat

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material3.AlertDialog
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
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.unit.dp
import com.tvcsoft.mathmate.core.api.Message
import com.tvcsoft.mathmate.ui.composer.ComposerController
import com.tvcsoft.mathmate.ui.composer.ComposerField
import com.tvcsoft.mathmate.ui.formula.FormulaSheet
import com.tvcsoft.mathmate.ui.theme.Brand
import kotlinx.coroutines.launch

/** Editing the student's last message in the same box, chips and all (web: MessageList's EditBubble). */
@Composable
fun EditMessageDialog(message: Message, onDismiss: () -> Unit, onSave: suspend (String) -> Boolean) {
    val controller = remember { ComposerController() }
    var saving by remember { mutableStateOf(false) }
    var formula by remember { mutableStateOf<Pair<String, Int>?>(null) }
    val scope = rememberUiScope()
    val text = controller.text.trim()
    fun save() {
        if (saving || text.isEmpty() || text == message.text) return
        saving = true
        scope.launch {
            onSave(text)
            saving = false
        }
    }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Sửa tin nhắn") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Surface(color = MaterialTheme.colorScheme.surfaceContainerLow, shape = RoundedCornerShape(14.dp)) {
                    ComposerField(
                        controller, "Tin nhắn",
                        modifier = Modifier.fillMaxWidth().heightIn(min = 60.dp).padding(horizontal = 12.dp),
                        initialText = message.text, autofocus = true, maxLines = 10, tag = "editText",
                        onSubmit = ::save,
                        onOpenFormula = { latex, position -> formula = latex to position },
                    )
                }
                Text("${Brand.APP_NAME} sẽ trả lời lại tin nhắn đã sửa (tốn 1 lượt AI).", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        },
        confirmButton = {
            TextButton(onClick = ::save, enabled = !saving && text.isNotEmpty() && text != message.text, modifier = Modifier.testTag("saveEdit")) { Text("Gửi lại") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Hủy") } },
    )
    formula?.let { (latex, position) ->
        FormulaSheet(latex, editingExisting = true, onDismiss = { formula = null }) { edited ->
            formula = null
            controller.replaceFormula(position, edited)
        }
    }
}
