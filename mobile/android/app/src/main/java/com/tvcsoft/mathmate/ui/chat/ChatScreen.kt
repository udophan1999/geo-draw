package com.tvcsoft.mathmate.ui.chat

import android.content.ClipData
import android.content.ClipboardManager
import android.content.Context
import androidx.compose.animation.AnimatedVisibility
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInVertically
import androidx.compose.animation.slideOutVertically
import androidx.compose.foundation.ExperimentalFoundationApi
import androidx.compose.foundation.Image
import androidx.compose.foundation.combinedClickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.imePadding
import androidx.compose.foundation.layout.navigationBarsPadding
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.ChangeHistory
import androidx.compose.material.icons.filled.ContentCopy
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Error
import androidx.compose.material.icons.filled.Info
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import com.tvcsoft.mathmate.ui.common.rememberUiScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import com.tvcsoft.mathmate.AppContainer
import com.tvcsoft.mathmate.R
import com.tvcsoft.mathmate.core.api.Example
import com.tvcsoft.mathmate.core.api.Message
import com.tvcsoft.mathmate.core.api.TutorAction
import com.tvcsoft.mathmate.core.api.TutorMode
import com.tvcsoft.mathmate.core.chat.PendingTurn
import com.tvcsoft.mathmate.core.chat.PreparedImage
import com.tvcsoft.mathmate.ui.common.AuthImage
import com.tvcsoft.mathmate.ui.composer.Composer
import com.tvcsoft.mathmate.ui.drawing.DrawingPanel
import com.tvcsoft.mathmate.ui.drawing.FigureCard
import com.tvcsoft.mathmate.ui.math.MathText
import com.tvcsoft.mathmate.ui.theme.Brand
import com.tvcsoft.mathmate.ui.theme.Haptics
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.withContext
import kotlinx.coroutines.launch

/**
 * A conversation with the tutor, or a new one when `conversationId` is null (web:
 * routes/ChatPage.tsx; iOS: ChatView). The figure lives in a bottom sheet.
 */
@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(container: AppContainer, conversationId: String?, onBack: () -> Unit, onCreated: (String) -> Unit) {
    val chat = container.chat
    val session = container.session
    val api = container.api
    val scope = rememberUiScope()
    val context = LocalContext.current
    var editing by remember { mutableStateOf<Message?>(null) }
    var showingFigure by remember { mutableStateOf(false) }

    val detail = conversationId?.let { chat.details[it] }
    val turn = conversationId?.let { chat.pending[it] }
    val chatMessages = detail?.messages?.filter { it.channel == Message.Channel.CHAT }.orEmpty()
    val figureMessages = detail?.messages?.filter { it.channel == Message.Channel.FIGURE }.orEmpty()
    val drawings = figureMessages.filter { it.hasDrawing && it.imageUrl != null }
    val figureLabel = conversationId?.let { chat.figures[it] }
    // Shown for geometry problems, or once a figure was asked for (web: hasFigurePanel).
    val hasFigure = figureMessages.isNotEmpty() || figureLabel != null || detail?.conversation?.isGeometry == true
    val figureFailed = figureLabel == null && figureMessages.lastOrNull()?.let { it.role == Message.Role.ASSISTANT && !it.hasDrawing } == true
    // The figure card goes after the last chat message sent before the newest figure message.
    val figureCardAfter = figureMessages.lastOrNull()?.let { newest -> chatMessages.lastOrNull { it.createdAt <= newest.createdAt }?.id }
    val busy = turn != null
    // Conversations from before the tutor have drawings only.
    val legacyProblem = if (detail != null && chatMessages.isEmpty() && turn == null && figureMessages.isNotEmpty()) detail.conversation.problem else null
    val lastUserId = chatMessages.lastOrNull { it.role == Message.Role.USER }?.id
    val listState = rememberLazyListState()

    LaunchedEffect(conversationId) { conversationId?.let { chat.load(it) } }
    // A conversation opens at its latest message and follows the reply as it streams.
    LaunchedEffect(chatMessages.size, turn?.reply?.length, turn?.label, figureLabel) {
        val count = listState.layoutInfo.totalItemsCount
        if (count > 0 && conversationId != null) listState.animateScrollToItem(count - 1)
    }

    suspend fun send(text: String, image: PreparedImage?): Boolean {
        val id = chat.send(text, image, conversationId) ?: return false
        // Navigation must happen on the main thread, wherever the request resumed.
        withContext(Dispatchers.Main) {
            Haptics.tick(context)
            if (conversationId == null) onCreated(id)
        }
        return true
    }

    // "Vẽ hình" in the composer when no figure is shown yet (geometry problems get the figure
    // button in the top bar, and their figure is drawn by itself).
    val canAskForFigure = detail != null && !detail.conversation.isGeometry && drawings.isEmpty() && figureLabel == null

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(detail?.conversation?.title ?: "Cuộc trò chuyện mới", maxLines = 1, overflow = TextOverflow.Ellipsis) },
                navigationIcon = { IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Quay lại") } },
                actions = {
                    if (detail != null && hasFigure) {
                        IconButton(onClick = { showingFigure = true }, modifier = Modifier.testTag("showFigure")) {
                            if (figureLabel != null) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                            else Icon(Icons.Filled.ChangeHistory, contentDescription = "Hình vẽ")
                        }
                    }
                },
            )
        },
        bottomBar = {
            Column(
                Modifier.navigationBarsPadding().imePadding().padding(horizontal = 12.dp, vertical = 8.dp).widthIn(max = 760.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp),
            ) {
                if (detail != null && (chatMessages.isNotEmpty() || legacyProblem != null)) {
                    TutorBar(detail.conversation, busy) { action ->
                        scope.launch { chat.send("", conversationId = conversationId, action = action) }
                    }
                }
                Composer(
                    placeholder = if (detail == null) "Nhập đề bài hoặc chụp ảnh đề…" else "Trả lời câu hỏi của gia sư, hoặc hỏi thêm…",
                    busy = busy || chat.sending,
                    onDraw = if (canAskForFigure) {
                        { scope.launch { if (conversationId != null && chat.drawFigure(conversationId)) showingFigure = true } }
                    } else {
                        null
                    },
                    onSend = ::send,
                )
            }
        },
    ) { padding ->
        Box(Modifier.padding(padding).fillMaxSize()) {
            LazyColumn(
                state = listState,
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
                verticalArrangement = Arrangement.spacedBy(18.dp),
                modifier = Modifier.fillMaxSize().testTag("messages"),
            ) {
                if (conversationId == null || (detail != null && chatMessages.isEmpty() && turn == null && legacyProblem == null)) {
                    item("welcome") { WelcomeMessages(container) { example -> scope.launch { send(example.problem, null) } } }
                }
                if (legacyProblem != null) item("legacy") { LegacyProblem(legacyProblem) }
                if (hasFigure && figureCardAfter == null && figureMessages.isNotEmpty()) {
                    item("figure") { FigureCard(drawings.lastOrNull(), figureLabel, figureFailed, api) { showingFigure = true } }
                }
                items(chatMessages, key = { it.id }) { message ->
                    Column(verticalArrangement = Arrangement.spacedBy(18.dp)) {
                        MessageRow(message, container, editable = !busy && message.id == lastUserId) { editing = message }
                        if (message.id == figureCardAfter) FigureCard(drawings.lastOrNull(), figureLabel, figureFailed, api) { showingFigure = true }
                    }
                }
                if (figureMessages.isEmpty() && figureLabel != null) {
                    item("figure-busy") { FigureCard(null, figureLabel, false, api) { showingFigure = true } }
                }
                if (turn != null) item("pending") { PendingRow(turn) }
            }
            if (conversationId != null && detail == null) {
                val error = chat.loadErrors[conversationId]
                if (error != null) {
                    Column(Modifier.align(Alignment.Center).padding(32.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                        Text("Không mở được", style = MaterialTheme.typography.titleMedium)
                        Text(error, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                } else {
                    CircularProgressIndicator(Modifier.align(Alignment.Center))
                }
            }
            NoticeBanner(container, Modifier.align(Alignment.TopCenter))
        }
    }

    if (showingFigure && conversationId != null) {
        ModalBottomSheet(onDismissRequest = { showingFigure = false }, sheetState = rememberModalBottomSheetState()) {
            DrawingPanel(conversationId, chat, api)
        }
    }
    editing?.let { message ->
        EditMessageDialog(message, onDismiss = { editing = null }) { text ->
            val id = conversationId ?: return@EditMessageDialog false
            chat.edit(id, message.id, text).also { if (it) editing = null }
        }
    }
}

private fun copy(context: Context, text: String) {
    val clipboard = context.getSystemService(ClipboardManager::class.java)
    clipboard?.setPrimaryClip(ClipData.newPlainText("MathMate", text))
}

@OptIn(ExperimentalFoundationApi::class)
@Composable
private fun MessageRow(message: Message, container: AppContainer, editable: Boolean, onEdit: () -> Unit) {
    var menu by remember { mutableStateOf(false) }
    val context = LocalContext.current
    val menuContent: @Composable () -> Unit = {
        DropdownMenu(expanded = menu, onDismissRequest = { menu = false }) {
            if (message.text.isNotEmpty()) {
                DropdownMenuItem(text = { Text("Sao chép") }, leadingIcon = { Icon(Icons.Filled.ContentCopy, null) }, onClick = { menu = false; copy(context, message.text) })
            }
            if (editable) {
                DropdownMenuItem(text = { Text("Sửa tin nhắn") }, leadingIcon = { Icon(Icons.Filled.Edit, null) }, onClick = { menu = false; onEdit() }, modifier = Modifier.testTag("editMessage"))
            }
        }
    }
    if (message.role == Message.Role.USER) {
        Row(Modifier.fillMaxWidth().testTag("userMessage")) {
            Spacer(Modifier.weight(1f).widthIn(min = 48.dp))
            Box {
                UserBubble(message.text, Modifier.combinedClickable(onClick = { if (editable) menu = true }, onLongClick = { menu = true })) {
                    message.imageUrl?.let { AuthImage(it, container.api, Modifier.heightIn(max = 220.dp).clip(RoundedCornerShape(10.dp))) }
                }
                menuContent()
            }
        }
    } else {
        AssistantRow(Modifier.testTag("assistantMessage")) {
            Box {
                Column(
                    Modifier.combinedClickable(onClick = {}, onLongClick = { menu = true }),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    if (message.isError) {
                        Surface(color = MaterialTheme.colorScheme.error.copy(alpha = 0.1f), shape = RoundedCornerShape(10.dp)) {
                            MathText(message.text, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(10.dp))
                        }
                    } else {
                        MathText(message.text)
                    }
                    if (message.meta.mode == TutorMode.SOLUTION && !message.isError) {
                        Surface(color = MaterialTheme.colorScheme.surfaceContainerHigh, shape = RoundedCornerShape(50)) {
                            Text("Lời giải chi tiết", style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.Medium, modifier = Modifier.padding(horizontal = 8.dp, vertical = 3.dp))
                        }
                    }
                }
                menuContent()
            }
        }
    }
}

@Composable
private fun UserBubble(text: String, modifier: Modifier = Modifier, image: @Composable () -> Unit = {}) {
    Surface(color = MaterialTheme.colorScheme.primary.copy(alpha = 0.12f), shape = RoundedCornerShape(18.dp), modifier = modifier) {
        Column(Modifier.padding(horizontal = 14.dp, vertical = 10.dp), horizontalAlignment = Alignment.End, verticalArrangement = Arrangement.spacedBy(8.dp)) {
            image()
            // Keep the student's line breaks (the web adds Markdown hard breaks too).
            if (text.isNotEmpty()) MathText(text, modifier = Modifier.widthIn(max = 600.dp), fill = false)
        }
    }
}

@Composable
private fun AssistantRow(modifier: Modifier = Modifier, content: @Composable () -> Unit) {
    Row(modifier.fillMaxWidth(), verticalAlignment = Alignment.Top) {
        Image(painterResource(R.drawable.logo), contentDescription = null, modifier = Modifier.size(26.dp).clip(RoundedCornerShape(7.dp)))
        Spacer(Modifier.width(10.dp))
        Box(Modifier.weight(1f)) { content() }
    }
}

@Composable
private fun PendingRow(turn: PendingTurn) {
    Column(verticalArrangement = Arrangement.spacedBy(18.dp)) {
        if (!turn.userSaved) {
            Row(Modifier.fillMaxWidth()) {
                Spacer(Modifier.weight(1f).widthIn(min = 48.dp))
                val preview = remember(turn.image) { turn.image?.let { android.graphics.BitmapFactory.decodeByteArray(it, 0, it.size) } }
                UserBubble(turn.text) {
                    preview?.let {
                        Image(it.asImageBitmap(), null, contentScale = ContentScale.Fit, modifier = Modifier.heightIn(max = 220.dp).clip(RoundedCornerShape(10.dp)))
                    }
                }
            }
        }
        if (turn.reply.isNotEmpty()) {
            AssistantRow(Modifier.testTag("streamingReply")) { MathText(turn.reply, cursor = true) }
        } else if (turn.label.isNotEmpty()) {
            AssistantRow {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                    Spacer(Modifier.width(8.dp))
                    Text(turn.label, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

@Composable
private fun LegacyProblem(problem: String) {
    Surface(color = MaterialTheme.colorScheme.surfaceContainerLow, shape = RoundedCornerShape(14.dp)) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text("Đề bài", style = MaterialTheme.typography.titleSmall)
            MathText(problem, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(
                "Cuộc trò chuyện này được tạo trước khi có gia sư. Nhắn một câu bất kỳ (ví dụ “em nên bắt đầu từ đâu?”) để được gợi ý giải.",
                style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

/** The greeting and example problems of an empty conversation. */
@Composable
private fun WelcomeMessages(container: AppContainer, onExample: (Example) -> Unit) {
    var examples by remember { mutableStateOf(emptyList<Example>()) }
    LaunchedEffect(Unit) { examples = try { container.api.examples() } catch (_: Exception) { emptyList() } }
    Column(Modifier.padding(top = 12.dp), verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(container.session.user?.let { "Chào ${it.name}!" } ?: "Chào bạn!", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold)
            Text("Gửi đề bài (gõ hoặc chụp ảnh), ${Brand.APP_NAME} sẽ gợi ý từng bước để em tự giải.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        if (examples.isNotEmpty()) {
            Text("Thử một bài mẫu", style = MaterialTheme.typography.titleMedium)
            for (example in examples) {
                Surface(
                    onClick = { onExample(example) },
                    shape = RoundedCornerShape(14.dp),
                    color = MaterialTheme.colorScheme.surfaceContainerLow,
                    modifier = Modifier.fillMaxWidth().testTag("example"),
                ) {
                    Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(example.topic.uppercase(), style = MaterialTheme.typography.labelSmall, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.primary)
                        Text(example.name, style = MaterialTheme.typography.titleSmall)
                        MathText(example.problem, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 3)
                    }
                }
            }
        }
    }
}

/** Errors and notes over the chat for a few seconds (web: the toasts). */
@Composable
private fun NoticeBanner(container: AppContainer, modifier: Modifier = Modifier) {
    val chat = container.chat
    val notice = chat.notice
    LaunchedEffect(notice?.id) {
        if (notice != null) {
            delay(5000)
            if (chat.notice?.id == notice.id) chat.notice = null
        }
    }
    AnimatedVisibility(notice != null, enter = slideInVertically() + fadeIn(), exit = slideOutVertically() + fadeOut(), modifier = modifier) {
        val shown = notice ?: return@AnimatedVisibility
        Surface(
            onClick = { chat.notice = null },
            shape = RoundedCornerShape(50),
            color = MaterialTheme.colorScheme.surfaceContainerHigh,
            shadowElevation = 4.dp,
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 6.dp).testTag("notice"),
        ) {
            Row(Modifier.padding(horizontal = 14.dp, vertical = 10.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    if (shown.isError) Icons.Filled.Error else Icons.Filled.Info, null,
                    tint = if (shown.isError) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
                    modifier = Modifier.size(18.dp),
                )
                Spacer(Modifier.width(8.dp))
                Text(shown.text, style = MaterialTheme.typography.bodySmall, color = if (shown.isError) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurface)
            }
        }
    }
}
