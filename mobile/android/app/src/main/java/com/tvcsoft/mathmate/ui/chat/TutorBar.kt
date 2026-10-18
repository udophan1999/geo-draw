package com.tvcsoft.mathmate.ui.chat

import androidx.compose.animation.animateColorAsState
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.FormatListNumbered
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.FilledTonalButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.semantics.clearAndSetSemantics
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.selected
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import com.tvcsoft.mathmate.core.api.Conversation
import com.tvcsoft.mathmate.core.api.TutorAction
import com.tvcsoft.mathmate.core.api.TutorMode
import com.tvcsoft.mathmate.ui.theme.Brand
import com.tvcsoft.mathmate.ui.theme.Haptics

/** The tutor's levels, in the order of geo_draw/tutor_prompts.py HINT_LEVELS (web: lib/hintLevels.ts). */
object HintLevels {
    val names = listOf("Hiểu đề", "Nhớ kiến thức", "Chiến lược", "Bước đầu tiên", "Sâu hơn nữa")
}

/** Hint or worked solution, the hint level and "Gợi ý sâu hơn" (web: chat/TutorBar.tsx). */
@Composable
fun TutorBar(conversation: Conversation, busy: Boolean, onAction: (TutorAction) -> Unit) {
    var confirmSolution by remember { mutableStateOf(false) }
    val solution = conversation.mode == TutorMode.SOLUTION
    val level = conversation.hintLevel.coerceIn(1, HintLevels.names.size)
    val context = LocalContext.current
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Surface(shape = CircleShape, color = MaterialTheme.colorScheme.surfaceContainerHigh) {
            Row(Modifier.padding(3.dp)) {
                ModeButton("Gợi ý", Icons.Filled.Lightbulb, active = !solution, enabled = !busy, tag = "modeHint") {
                    if (solution) onAction(TutorAction.HINT)
                }
                ModeButton("Lời giải", Icons.Filled.FormatListNumbered, active = solution, enabled = !busy, tag = "modeSolution") {
                    if (!solution) confirmSolution = true
                }
            }
        }
        Spacer(Modifier.weight(1f))
        when {
            solution -> Text("Đang xem lời giải đầy đủ", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            conversation.solved -> Row(verticalAlignment = Alignment.CenterVertically) {
                Dots(HintLevels.names.size, Brand.success)
                Spacer(Modifier.width(6.dp))
                Icon(Icons.Filled.CheckCircle, null, tint = Brand.success, modifier = Modifier.size(16.dp))
                Text(" Đã giải xong", style = MaterialTheme.typography.labelMedium, fontWeight = FontWeight.SemiBold, color = Brand.success, modifier = Modifier.testTag("solved"))
            }
            else -> Row(verticalAlignment = Alignment.CenterVertically) {
                Column(
                    horizontalAlignment = Alignment.End,
                    modifier = Modifier.testTag("hintLevel").clearAndSetSemantics {
                        contentDescription = "Bậc $level/${HintLevels.names.size}: ${HintLevels.names[level - 1]}"
                    },
                ) {
                    Dots(level, MaterialTheme.colorScheme.primary)
                    Text(HintLevels.names[level - 1], style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Spacer(Modifier.width(8.dp))
                FilledTonalButton(
                    onClick = {
                        Haptics.tick(context)
                        onAction(TutorAction.DEEPER)
                    },
                    enabled = !busy && level < HintLevels.names.size,
                    contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 12.dp, vertical = 4.dp),
                    modifier = Modifier.testTag("deeperHint").semantics { contentDescription = "Gợi ý sâu hơn" },
                ) {
                    Icon(Icons.Filled.AutoAwesome, null, modifier = Modifier.size(16.dp))
                    Spacer(Modifier.width(4.dp))
                    Text("Sâu hơn", style = MaterialTheme.typography.labelLarge)
                }
            }
        }
    }
    if (confirmSolution) {
        AlertDialog(
            onDismissRequest = { confirmSolution = false },
            title = { Text("Xem lời giải chi tiết?") },
            text = {
                Text("Tự nghĩ ra lời giải sẽ giúp nhớ lâu hơn. Nếu đã thử mà vẫn bí, hoặc muốn đối chiếu bài làm, hãy xem lời giải đầy đủ. Bạn có thể quay lại chế độ gợi ý bất cứ lúc nào.")
            },
            confirmButton = {
                TextButton(onClick = { confirmSolution = false; onAction(TutorAction.SOLUTION) }, modifier = Modifier.testTag("confirmSolution")) {
                    Text("Xem lời giải")
                }
            },
            dismissButton = { TextButton(onClick = { confirmSolution = false }) { Text("Tiếp tục tự làm") } },
        )
    }
}

@Composable
private fun ModeButton(title: String, icon: ImageVector, active: Boolean, enabled: Boolean, tag: String, onClick: () -> Unit) {
    val background by animateColorAsState(if (active) MaterialTheme.colorScheme.surface else Color.Transparent, label = "mode")
    val content = if (active) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant
    Row(
        Modifier
            .clip(CircleShape)
            .background(background)
            .clickable(enabled = enabled, role = Role.Tab, onClick = onClick)
            .padding(horizontal = 10.dp, vertical = 6.dp)
            .semantics { selected = active }
            .testTag(tag),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(icon, null, tint = content, modifier = Modifier.size(16.dp))
        Spacer(Modifier.width(4.dp))
        Text(title, style = MaterialTheme.typography.labelLarge, color = content)
    }
}

@Composable
private fun Dots(filled: Int, color: Color) {
    Row(horizontalArrangement = Arrangement.spacedBy(3.dp)) {
        repeat(HintLevels.names.size) { index ->
            Box(
                Modifier
                    .size(width = 12.dp, height = 5.dp)
                    .clip(RoundedCornerShape(3.dp))
                    .background(if (index < filled) color else MaterialTheme.colorScheme.outlineVariant),
            )
        }
    }
}
