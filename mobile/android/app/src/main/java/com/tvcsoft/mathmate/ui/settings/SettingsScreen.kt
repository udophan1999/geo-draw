package com.tvcsoft.mathmate.ui.settings

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.selection.selectable
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ExpandLess
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.RadioButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import com.tvcsoft.mathmate.ui.common.rememberUiScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import com.tvcsoft.mathmate.core.api.ApiError
import com.tvcsoft.mathmate.core.api.DrawSettings
import com.tvcsoft.mathmate.core.auth.SessionStore
import com.tvcsoft.mathmate.ui.math.MathText
import com.tvcsoft.mathmate.ui.theme.Brand
import com.tvcsoft.mathmate.ui.theme.Haptics
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

/** Drawing settings, the THCS drawing conventions and the account (web: SettingsDialog; iOS: SettingsView). */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun SettingsScreen(session: SessionStore, onClose: () -> Unit) {
    var draft by remember { mutableStateOf<DrawSettings?>(null) }
    var help by remember { mutableStateOf<String?>(null) }
    var showHelp by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var saving by remember { mutableStateOf(false) }
    var deleting by remember { mutableStateOf(false) }
    val scope = rememberUiScope()
    val context = LocalContext.current
    val aiAvailable = session.me?.aiAvailable ?: true

    LaunchedEffect(Unit) {
        try {
            val settings = session.api.settings()
            draft = if (!aiAvailable) settings.copy(mode = DrawSettings.Mode.PARSER) else settings
        } catch (failure: ApiError) {
            error = failure.message
        }
        help = try { session.api.help() } catch (_: ApiError) { null }
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Cài đặt") },
                navigationIcon = { IconButton(onClick = onClose) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Đóng") } },
                actions = {
                    TextButton(
                        onClick = {
                            val settings = draft ?: return@TextButton
                            saving = true
                            scope.launch {
                                try {
                                    session.api.saveSettings(settings)
                                    // Navigation must happen on the main thread, wherever the request resumed.
                                    withContext(Dispatchers.Main) {
                                        Haptics.success(context)
                                        onClose()
                                    }
                                } catch (failure: ApiError) {
                                    error = failure.message
                                } finally {
                                    saving = false
                                }
                            }
                        },
                        enabled = draft != null && !saving,
                        modifier = Modifier.testTag("saveSettings"),
                    ) { Text("Lưu") }
                },
            )
        },
    ) { padding ->
        Column(Modifier.padding(padding).fillMaxSize().verticalScroll(rememberScrollState()).padding(16.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            val settings = draft
            if (settings == null) {
                if (error == null) CircularProgressIndicator(Modifier.align(Alignment.CenterHorizontally))
            } else {
                Section("Cách vẽ hình")
                Choice("${Brand.APP_NAME} AI", settings.mode == DrawSettings.Mode.AI, aiAvailable) { draft = settings.copy(mode = DrawSettings.Mode.AI) }
                Choice("Parser nhanh", settings.mode == DrawSettings.Mode.PARSER, true) { draft = settings.copy(mode = DrawSettings.Mode.PARSER) }
                Note(
                    when {
                        !aiAvailable -> "Máy chủ chưa cấu hình khóa AI."
                        settings.mode == DrawSettings.Mode.AI -> "Vẽ được đề phức tạp. Mỗi lần vẽ tốn 1 lượt AI."
                        else -> "Chạy trên máy chủ, không tốn lượt AI; chỉ hiểu các mẫu cơ bản."
                    },
                )
                HorizontalDivider()
                if (settings.mode == DrawSettings.Mode.AI) {
                    Section("Mô hình AI")
                    Choice("Nhanh — hợp đa số đề", settings.model == DrawSettings.Model.FLASH, true) { draft = settings.copy(model = DrawSettings.Model.FLASH) }
                    Choice("Chuyên sâu — ưu tiên chất lượng", settings.model == DrawSettings.Model.PRO, true) { draft = settings.copy(model = DrawSettings.Model.PRO) }
                }
                Section("Chất lượng hình")
                for ((quality, label) in listOf(DrawSettings.Quality.L to "Thấp — nhanh nhất", DrawSettings.Quality.M to "Vừa", DrawSettings.Quality.H to "Cao — chậm hơn")) {
                    Choice(label, settings.quality == quality, true) { draft = settings.copy(quality = quality) }
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Text("Video hoạt hình", modifier = Modifier.weight(1f))
                    Switch(settings.animate, { draft = settings.copy(animate = it) })
                }
                Note("Gia sư luôn dùng ${Brand.APP_NAME} AI; các lựa chọn trên áp dụng cho việc vẽ hình.")
            }
            help?.let { markdown ->
                HorizontalDivider()
                Row(
                    Modifier.fillMaxWidth().selectable(showHelp, onClick = { showHelp = !showHelp }),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text("Quy ước hình học THCS", style = MaterialTheme.typography.titleSmall, modifier = Modifier.weight(1f))
                    Icon(if (showHelp) Icons.Filled.ExpandLess else Icons.Filled.ExpandMore, null)
                }
                if (showHelp) MathText(markdown, style = MaterialTheme.typography.bodySmall)
            }
            session.user?.let { user ->
                HorizontalDivider()
                Section("Tài khoản")
                Row { Text("Tên đăng nhập", Modifier.weight(1f)); Text(user.name, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                session.me?.quota?.let { quota ->
                    Row { Text("Lượt AI hôm nay", Modifier.weight(1f)); Text("${quota.used}/${quota.limit}", color = MaterialTheme.colorScheme.onSurfaceVariant) }
                }
                TextButton(onClick = { onClose(); scope.launch { session.logout() } }) { Text("Đăng xuất", color = MaterialTheme.colorScheme.error) }
                TextButton(onClick = { deleting = true }, modifier = Modifier.testTag("deleteAccount")) { Text("Xóa tài khoản…", color = MaterialTheme.colorScheme.error) }
                Note("Xóa vĩnh viễn tài khoản và mọi dữ liệu.")
            }
            error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        }
    }
    if (deleting) DeleteAccountDialog(session) { deleting = false }
}

@Composable
private fun Section(title: String) = Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)

@Composable
private fun Note(text: String) = Text(text, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)

@Composable
private fun Choice(label: String, selected: Boolean, enabled: Boolean, onSelect: () -> Unit) {
    Row(
        Modifier.fillMaxWidth().selectable(selected, enabled = enabled, role = Role.RadioButton, onClick = onSelect),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        RadioButton(selected, onClick = null, enabled = enabled)
        Text(label, modifier = Modifier.padding(start = 8.dp), color = if (enabled) MaterialTheme.colorScheme.onSurface else MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

/** Delete the account for good, after the password is typed again (web: DeleteAccountDialog). */
@Composable
private fun DeleteAccountDialog(session: SessionStore, onDismiss: () -> Unit) {
    var password by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberUiScope()
    val context = LocalContext.current
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Xóa tài khoản?") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("Mọi cuộc trò chuyện, hình vẽ và cài đặt của bạn sẽ bị xóa vĩnh viễn, không khôi phục được.")
                OutlinedTextField(
                    password, { password = it },
                    label = { Text("Nhập mật khẩu để xác nhận") },
                    singleLine = true,
                    visualTransformation = PasswordVisualTransformation(),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Password),
                    modifier = Modifier.testTag("deletePassword"),
                )
                error?.let { Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.testTag("deleteError")) }
            }
        },
        confirmButton = {
            TextButton(
                onClick = {
                    busy = true
                    scope.launch {
                        try {
                            session.deleteAccount(password)
                            Haptics.success(context)
                            onDismiss()
                        } catch (failure: ApiError) {
                            error = failure.message
                            password = ""
                        } finally {
                            busy = false
                        }
                    }
                },
                enabled = password.isNotEmpty() && !busy,
                modifier = Modifier.testTag("confirmDeleteAccount"),
            ) { Text("Xóa vĩnh viễn", color = MaterialTheme.colorScheme.error) }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Hủy") } },
    )
}
