package com.tvcsoft.mathmate.ui.auth

import androidx.compose.animation.AnimatedContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SuggestionChip
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import com.tvcsoft.mathmate.ui.common.rememberUiScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import com.tvcsoft.mathmate.R
import com.tvcsoft.mathmate.core.api.ApiError
import com.tvcsoft.mathmate.core.auth.SessionStore
import com.tvcsoft.mathmate.ui.theme.Brand
import com.tvcsoft.mathmate.ui.theme.Haptics
import kotlinx.coroutines.launch

/** Sign in, sign up or try without an account (web: routes/auth.tsx; iOS: WelcomeView). */
@Composable
fun WelcomeScreen(session: SessionStore) {
    var registering by rememberSaveable { mutableStateOf(false) }
    val scope = rememberUiScope()
    Surface(color = MaterialTheme.colorScheme.surfaceContainerLow, modifier = Modifier.fillMaxSize()) {
        Column(
            Modifier
                .fillMaxSize()
                .safeDrawingPadding()
                .imePadding()
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 16.dp, vertical = 24.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(20.dp),
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(6.dp)) {
                Image(
                    painterResource(R.drawable.logo), contentDescription = null,
                    modifier = Modifier.size(72.dp).clip(RoundedCornerShape(17.dp)),
                )
                Text(Brand.APP_NAME, style = MaterialTheme.typography.headlineLarge, fontWeight = FontWeight.Bold)
                Text(
                    "Gia sư toán THCS – THPT, kèm hình vẽ minh họa",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    textAlign = TextAlign.Center,
                )
            }
            session.startError?.let {
                Text(it, color = Color.Warning, style = MaterialTheme.typography.bodySmall, textAlign = TextAlign.Center)
            }
            Card(
                modifier = Modifier.widthIn(max = 420.dp).fillMaxWidth(),
                colors = CardDefaults.cardColors(containerColor = MaterialTheme.colorScheme.surface),
                shape = RoundedCornerShape(20.dp),
            ) {
                AnimatedContent(registering, label = "auth") { register ->
                    Column(Modifier.padding(20.dp)) {
                        if (register) RegisterForm(session) { registering = false } else LoginForm(session) { registering = true }
                    }
                }
            }
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                TextButton(onClick = { scope.launch { session.continueAsGuest() } }, modifier = Modifier.testTag("tryAsGuest")) {
                    Text("Dùng thử không cần tài khoản →")
                }
                Text(
                    "Khi dùng thử, lịch sử chỉ lưu trên máy này.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
    }
}

private object Color {
    val Warning = androidx.compose.ui.graphics.Color(0xFFD97706)
}

@Composable
private fun Field(
    label: String,
    value: String,
    onValue: (String) -> Unit,
    tag: String,
    secure: Boolean = false,
    placeholder: String? = null,
    last: Boolean = false,
    onDone: () -> Unit = {},
) {
    OutlinedTextField(
        value = value,
        onValueChange = onValue,
        label = { Text(label) },
        placeholder = placeholder?.let { { Text(it) } },
        singleLine = true,
        visualTransformation = if (secure) PasswordVisualTransformation() else androidx.compose.ui.text.input.VisualTransformation.None,
        keyboardOptions = KeyboardOptions(
            keyboardType = if (secure) KeyboardType.Password else KeyboardType.Text,
            autoCorrectEnabled = false,
            imeAction = if (last) ImeAction.Done else ImeAction.Next,
        ),
        keyboardActions = KeyboardActions(onDone = { onDone() }),
        modifier = Modifier.fillMaxWidth().testTag(tag),
    )
}

@Composable
private fun FormError(message: String?) {
    if (message != null) {
        Text(message, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall, modifier = Modifier.testTag("authError"))
    }
}

@Composable
private fun SubmitButton(title: String, busy: Boolean, enabled: Boolean, tag: String, onClick: () -> Unit) {
    Button(onClick = onClick, enabled = enabled && !busy, modifier = Modifier.fillMaxWidth().height(48.dp).testTag(tag)) {
        if (busy) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp) else Text(title)
    }
}

@Composable
private fun LoginForm(session: SessionStore, onRegister: () -> Unit) {
    var username by rememberSaveable { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberUiScope()
    val context = LocalContext.current
    fun submit() {
        if (busy || username.isEmpty() || password.isEmpty()) return
        busy = true
        scope.launch {
            try {
                session.login(username, password)
            } catch (failure: ApiError) {
                error = failure.message
                password = ""
                Haptics.tick(context)
            } finally {
                busy = false
            }
        }
    }
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Column {
            Text("Đăng nhập", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text("Đăng nhập để xem lại lịch sử hỏi đáp.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Field("Tên đăng nhập", username, { username = it }, "username")
        Field("Mật khẩu", password, { password = it }, "password", secure = true, last = true, onDone = ::submit)
        FormError(error)
        SubmitButton("Đăng nhập", busy, username.isNotEmpty() && password.isNotEmpty(), "loginButton", ::submit)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
            Text("Chưa có tài khoản?", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodyMedium)
            TextButton(onClick = onRegister, modifier = Modifier.testTag("showRegister")) { Text("Đăng ký") }
        }
    }
}

@Composable
private fun RegisterForm(session: SessionStore, onLogin: () -> Unit) {
    var username by rememberSaveable { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var confirm by remember { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    var suggestions by remember { mutableStateOf(emptyList<String>()) }
    var busy by remember { mutableStateOf(false) }
    val scope = rememberUiScope()
    val context = LocalContext.current
    val minPassword = 6
    fun submit() {
        if (busy) return
        suggestions = emptyList()
        // The same checks as the web, before the request.
        if (password.length < minPassword) {
            error = "Mật khẩu phải có ít nhất $minPassword ký tự."
            return
        }
        if (password != confirm) {
            error = "Hai lần nhập mật khẩu không khớp."
            return
        }
        busy = true
        scope.launch {
            try {
                session.register(username, password)
            } catch (failure: ApiError) {
                error = failure.message
                suggestions = failure.suggestions
                Haptics.tick(context)
            } finally {
                busy = false
            }
        }
    }
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Column {
            Text("Đăng ký", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
            Text("Tạo tài khoản để lưu lại các bài đã hỏi.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Field("Tên đăng nhập", username, { username = it }, "username", placeholder = "Ví dụ: an.nguyen.7a")
        Field("Mật khẩu", password, { password = it }, "password", secure = true, placeholder = "Ít nhất $minPassword ký tự")
        Field("Nhập lại mật khẩu", confirm, { confirm = it }, "confirmPassword", secure = true, last = true, onDone = ::submit)
        FormError(error)
        if (suggestions.isNotEmpty()) {
            Text("Gợi ý tên còn trống (chạm để dùng):", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                for (name in suggestions) {
                    SuggestionChip(onClick = {
                        username = name
                        error = null
                        suggestions = emptyList()
                    }, label = { Text(name) }, modifier = Modifier.testTag("suggestion"))
                }
            }
        }
        SubmitButton("Đăng ký", busy, username.isNotEmpty() && password.isNotEmpty(), "registerButton", ::submit)
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
            Text("Đã có tài khoản?", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodyMedium)
            TextButton(onClick = onLogin, modifier = Modifier.testTag("showLogin")) { Text("Đăng nhập") }
        }
        Spacer(Modifier.height(0.dp))
    }
}
