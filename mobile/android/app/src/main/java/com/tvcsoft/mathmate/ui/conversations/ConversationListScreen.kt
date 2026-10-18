package com.tvcsoft.mathmate.ui.conversations

import android.text.format.DateUtils
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.background
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Logout
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.FormatListNumbered
import androidx.compose.material.icons.filled.Lightbulb
import androidx.compose.material.icons.filled.Login
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.outlined.EditNote
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
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
import androidx.compose.material3.pulltorefresh.PullToRefreshBox
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import com.tvcsoft.mathmate.ui.common.rememberUiScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.tvcsoft.mathmate.core.api.Conversation
import com.tvcsoft.mathmate.core.api.TutorMode
import com.tvcsoft.mathmate.core.auth.SessionStore
import com.tvcsoft.mathmate.core.chat.ConversationsStore
import com.tvcsoft.mathmate.ui.theme.Brand
import kotlinx.coroutines.launch

/** The list of conversations with "new", rename and delete (web: Sidebar.tsx; iOS: ConversationListView). */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ConversationListScreen(
    session: SessionStore,
    conversations: ConversationsStore,
    onOpen: (String) -> Unit,
    onNew: () -> Unit,
    onSettings: () -> Unit,
) {
    val scope = rememberUiScope()
    var refreshing by remember { mutableStateOf(false) }
    var renaming by remember { mutableStateOf<Conversation?>(null) }
    var deleting by remember { mutableStateOf<Conversation?>(null) }
    LaunchedEffect(Unit) { if (!conversations.loaded) conversations.load() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(Brand.APP_NAME, fontWeight = FontWeight.Bold) },
                navigationIcon = { AccountMenu(session, onSettings) },
                actions = {
                    IconButton(onClick = onNew, modifier = Modifier.testTag("newConversation")) {
                        Icon(Icons.Outlined.EditNote, contentDescription = "Cuộc trò chuyện mới")
                    }
                },
            )
        },
    ) { padding ->
        PullToRefreshBox(
            isRefreshing = refreshing,
            onRefresh = {
                refreshing = true
                scope.launch {
                    conversations.load()
                    refreshing = false
                }
            },
            modifier = Modifier.padding(padding).fillMaxSize(),
        ) {
            LazyColumn(Modifier.fillMaxSize().testTag("conversationList")) {
                if (session.isGuest) item { GuestNotice(session) }
                items(conversations.items, key = { it.id }) { conversation ->
                    ConversationRow(
                        conversation,
                        onOpen = { onOpen(conversation.id) },
                        onRename = { renaming = conversation },
                        onDelete = { deleting = conversation },
                    )
                    HorizontalDivider(Modifier.padding(start = 16.dp), color = MaterialTheme.colorScheme.surfaceContainerHigh)
                }
            }
            when {
                !conversations.loaded -> CircularProgressIndicator(Modifier.align(Alignment.Center))
                conversations.items.isEmpty() -> Column(
                    Modifier.align(Alignment.Center).padding(32.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    Text("Chưa có cuộc trò chuyện", style = MaterialTheme.typography.titleMedium)
                    Text("Gửi đề bài đầu tiên để bắt đầu.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Button(onClick = onNew) { Text("Cuộc trò chuyện mới") }
                }
            }
        }
    }

    renaming?.let { conversation ->
        var title by remember(conversation.id) { mutableStateOf(conversation.title) }
        AlertDialog(
            onDismissRequest = { renaming = null },
            title = { Text("Đổi tên cuộc trò chuyện") },
            text = { OutlinedTextField(title, { title = it }, singleLine = true, label = { Text("Tên mới") }, modifier = Modifier.testTag("renameField")) },
            confirmButton = {
                TextButton(onClick = {
                    renaming = null
                    scope.launch { conversations.rename(conversation, title) }
                }) { Text("Lưu") }
            },
            dismissButton = { TextButton(onClick = { renaming = null }) { Text("Hủy") } },
        )
    }
    deleting?.let { conversation ->
        AlertDialog(
            onDismissRequest = { deleting = null },
            title = { Text("Xóa cuộc trò chuyện?") },
            text = { Text("«${conversation.title}» và các hình vẽ trong đó sẽ bị xóa vĩnh viễn.") },
            confirmButton = {
                TextButton(onClick = {
                    deleting = null
                    scope.launch { conversations.delete(conversation) }
                }, modifier = Modifier.testTag("confirmDelete")) { Text("Xóa", color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = { TextButton(onClick = { deleting = null }) { Text("Hủy") } },
        )
    }
    conversations.error?.takeIf { conversations.loaded }?.let { message ->
        AlertDialog(
            onDismissRequest = { conversations.error = null },
            title = { Text("Có lỗi") },
            text = { Text(message) },
            confirmButton = { TextButton(onClick = { conversations.error = null }) { Text("OK") } },
        )
    }
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun ConversationRow(conversation: Conversation, onOpen: () -> Unit, onRename: () -> Unit, onDelete: () -> Unit) {
    var menu by remember { mutableStateOf(false) }
    Row(
        Modifier
            .fillMaxWidth()
            .combinedClickable(onClick = onOpen, onLongClick = { menu = true })
            .padding(start = 16.dp, top = 10.dp, bottom = 10.dp, end = 4.dp)
            .testTag("conversation"),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
            Text(conversation.title, maxLines = 1, overflow = TextOverflow.Ellipsis, style = MaterialTheme.typography.bodyLarge)
            Row(verticalAlignment = Alignment.CenterVertically) {
                val (icon, label, tint) = when {
                    conversation.solved -> Triple(Icons.Filled.CheckCircle, "Đã giải xong", Brand.success)
                    conversation.mode == TutorMode.SOLUTION -> Triple(Icons.Filled.FormatListNumbered, "Lời giải", MaterialTheme.colorScheme.onSurfaceVariant)
                    else -> Triple(Icons.Filled.Lightbulb, "Gợi ý bậc ${conversation.hintLevel}", MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Status(icon, label, tint)
                Spacer(Modifier.weight(1f))
                Text(
                    DateUtils.getRelativeTimeSpanString((conversation.updatedAt * 1000).toLong()).toString(),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                )
            }
        }
        Box {
            IconButton(onClick = { menu = true }) { Icon(Icons.Filled.MoreVert, contentDescription = "Tùy chọn") }
            DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
                DropdownMenuItem(text = { Text("Đổi tên") }, leadingIcon = { Icon(Icons.Filled.Edit, null) }, onClick = { menu = false; onRename() })
                DropdownMenuItem(
                    text = { Text("Xóa", color = MaterialTheme.colorScheme.error) },
                    leadingIcon = { Icon(Icons.Filled.Delete, null, tint = MaterialTheme.colorScheme.error) },
                    onClick = { menu = false; onDelete() },
                    modifier = Modifier.testTag("deleteConversation"),
                )
            }
        }
    }
}

@Composable
private fun Status(icon: ImageVector, label: String, tint: androidx.compose.ui.graphics.Color) {
    Icon(icon, contentDescription = null, tint = tint, modifier = Modifier.size(14.dp))
    Spacer(Modifier.width(4.dp))
    Text(label, style = MaterialTheme.typography.labelSmall, color = tint)
}

@Composable
private fun GuestNotice(session: SessionStore) {
    Surface(
        color = MaterialTheme.colorScheme.secondaryContainer,
        shape = RoundedCornerShape(14.dp),
        modifier = Modifier.fillMaxWidth().padding(12.dp),
    ) {
        Row(Modifier.padding(14.dp), verticalAlignment = Alignment.CenterVertically) {
            Text("Đăng nhập để lưu lại lịch sử hỏi đáp", style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
            Button(onClick = { session.showWelcome() }) { Text("Đăng nhập") }
        }
    }
}

/** The account at the top of the list: settings, sign out (web: AccountBox). */
@Composable
private fun AccountMenu(session: SessionStore, onSettings: () -> Unit) {
    var open by remember { mutableStateOf(false) }
    val scope = rememberUiScope()
    val user = session.user
    Box {
        IconButton(onClick = { open = true }, modifier = Modifier.testTag("accountMenu")) {
            if (user != null) {
                Box(
                    Modifier.size(30.dp).background(MaterialTheme.colorScheme.primary, CircleShape),
                    contentAlignment = Alignment.Center,
                ) {
                    Text(user.name.take(1).uppercase(), color = MaterialTheme.colorScheme.onPrimary, fontWeight = FontWeight.Bold)
                }
            } else {
                Icon(Icons.Filled.AccountCircle, contentDescription = "Tài khoản")
            }
        }
        DropdownMenu(expanded = open, onDismissRequest = { open = false }) {
            if (user != null) {
                Text(user.name, style = MaterialTheme.typography.labelLarge, modifier = Modifier.padding(horizontal = 16.dp, vertical = 8.dp))
            }
            DropdownMenuItem(text = { Text("Cài đặt") }, leadingIcon = { Icon(Icons.Filled.Settings, null) }, onClick = { open = false; onSettings() }, modifier = Modifier.testTag("openSettings"))
            if (user != null) {
                DropdownMenuItem(
                    text = { Text("Đăng xuất") },
                    leadingIcon = { Icon(Icons.AutoMirrored.Filled.Logout, null) },
                    onClick = { open = false; scope.launch { session.logout() } },
                )
            } else {
                DropdownMenuItem(text = { Text("Đăng nhập") }, leadingIcon = { Icon(Icons.Filled.Login, null) }, onClick = { open = false; session.showWelcome() })
            }
        }
    }
}
