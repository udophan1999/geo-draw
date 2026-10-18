package com.tvcsoft.mathmate.ui.drawing

import android.content.Context
import android.content.Intent
import android.graphics.Bitmap
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.gestures.detectTapGestures
import androidx.compose.foundation.gestures.detectTransformGestures
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.safeDrawingPadding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.sizeIn
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.ChangeHistory
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.Fullscreen
import androidx.compose.material.icons.filled.Share
import androidx.compose.material.icons.filled.Warning
import androidx.compose.material.icons.filled.ZoomIn
import androidx.compose.material.icons.filled.ZoomOut
import androidx.compose.material.icons.filled.ZoomOutMap
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import com.tvcsoft.mathmate.ui.common.rememberUiScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.clipToBounds
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.pointer.pointerInput
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalFocusManager
import androidx.compose.ui.platform.testTag
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.compose.ui.window.Dialog
import androidx.compose.ui.window.DialogProperties
import androidx.core.content.FileProvider
import androidx.media3.common.MediaItem
import androidx.media3.exoplayer.ExoPlayer
import androidx.media3.ui.PlayerView
import com.tvcsoft.mathmate.R
import com.tvcsoft.mathmate.core.api.ApiClient
import com.tvcsoft.mathmate.core.api.ApiError
import com.tvcsoft.mathmate.core.api.Message
import com.tvcsoft.mathmate.core.chat.ChatStore
import com.tvcsoft.mathmate.ui.common.ImageStore
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import java.io.File

/**
 * The figure of a conversation (web: drawing/DrawingPanel.tsx; iOS: DrawingPanel): the versions
 * drawn so far, progress while one is drawn, the failure with "Vẽ lại", the "Yêu cầu chỉnh hình"
 * box, the video and sharing.
 */
@Composable
fun DrawingPanel(conversationId: String, chat: ChatStore, api: ApiClient) {
    val messages = chat.details[conversationId]?.messages?.filter { it.channel == Message.Channel.FIGURE }.orEmpty()
    val drawings = messages.filter { it.hasDrawing && it.imageUrl != null }
    val requests = messages.filter { it.role == Message.Role.USER && it.text.isNotEmpty() }.map { it.text }
    val busyLabel = chat.figures[conversationId]
    // The last drawing turn failed (an assistant figure message without a drawing).
    val failure = messages.lastOrNull()?.takeIf { busyLabel == null && it.role == Message.Role.ASSISTANT && !it.hasDrawing }
    // A pick holds until a new drawing arrives, which is then shown (web: pickKey).
    var picked by remember(drawings.size) { mutableStateOf<String?>(null) }
    val shown = drawings.firstOrNull { it.id == picked } ?: drawings.lastOrNull()
    val scope = rememberUiScope()
    val scroll = rememberScrollState()
    LaunchedEffect(drawings.size) { scroll.animateScrollTo(0) }

    Column(
        Modifier.verticalScroll(scroll).padding(16.dp).testTag("drawingPanel"),
        verticalArrangement = Arrangement.spacedBy(16.dp),
    ) {
        if (shown != null) {
            val index = drawings.indexOf(shown)
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Hình vẽ", style = MaterialTheme.typography.titleMedium)
                    Text(
                        if (index == drawings.lastIndex) "Phiên bản mới nhất" else "Phiên bản ${index + 1}/${drawings.size}",
                        style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.testTag("drawingVersion"),
                    )
                }
                if (drawings.size > 1) {
                    Row(horizontalArrangement = Arrangement.spacedBy(4.dp)) {
                        drawings.forEachIndexed { offset, drawing ->
                            val selected = drawing.id == shown.id
                            Surface(
                                onClick = { picked = drawing.id },
                                shape = RoundedCornerShape(7.dp),
                                color = if (selected) MaterialTheme.colorScheme.primary else MaterialTheme.colorScheme.surfaceContainerHigh,
                                modifier = Modifier.sizeIn(minWidth = 30.dp, minHeight = 28.dp).semantics { contentDescription = "Phiên bản ${offset + 1}" }.testTag("version-${offset + 1}"),
                            ) {
                                Box(contentAlignment = Alignment.Center) {
                                    Text("${offset + 1}", style = MaterialTheme.typography.labelLarge, color = if (selected) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface)
                                }
                            }
                        }
                    }
                }
                shown.imageUrl?.let { ShareDrawing(it, api) }
            }
            Status(busyLabel, failure) { scope.launch { chat.drawFigure(conversationId) } }
            shown.imageUrl?.let { DrawingImage(it, api) }
            RefineBox(busyLabel != null, requests) { text -> chat.drawFigure(conversationId, text) }
            shown.videoUrl?.let { DrawingVideo(it, api) }
        } else {
            Column(Modifier.fillMaxWidth().heightIn(min = 280.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(14.dp, Alignment.CenterVertically)) {
                if (busyLabel != null) {
                    CircularProgressIndicator()
                } else {
                    Image(androidx.compose.ui.res.painterResource(R.drawable.logo), null, modifier = Modifier.size(56.dp).clip(RoundedCornerShape(13.dp)).graphicsLayer { alpha = 0.3f })
                }
                Text(busyLabel ?: "Hình vẽ sẽ hiện ở đây", color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (busyLabel == null && failure == null) {
                    Button(onClick = { scope.launch { chat.drawFigure(conversationId) } }, modifier = Modifier.testTag("drawNow")) { Text("Vẽ hình") }
                }
                if (failure != null) Status(null, failure) { scope.launch { chat.drawFigure(conversationId) } }
            }
        }
    }
}

@Composable
private fun Status(busyLabel: String?, failure: Message?, onRedraw: () -> Unit) {
    if (busyLabel != null) {
        Row(verticalAlignment = Alignment.CenterVertically, modifier = Modifier.testTag("drawingProgress")) {
            CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
            Spacer(Modifier.width(8.dp))
            Text(busyLabel, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    } else if (failure != null) {
        Surface(color = MaterialTheme.colorScheme.error.copy(alpha = 0.1f), shape = RoundedCornerShape(12.dp), modifier = Modifier.testTag("drawingFailure")) {
            Row(Modifier.padding(12.dp), verticalAlignment = Alignment.Top) {
                Icon(Icons.Filled.Warning, null, tint = MaterialTheme.colorScheme.error)
                Spacer(Modifier.width(8.dp))
                Text(failure.text, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodyMedium, modifier = Modifier.weight(1f))
                TextButton(onClick = onRedraw, modifier = Modifier.testTag("redraw")) { Text("Vẽ lại", fontWeight = FontWeight.SemiBold) }
            }
        }
    }
}

@Composable
private fun RefineBox(busy: Boolean, requests: List<String>, onRefine: suspend (String) -> Boolean) {
    var request by remember { mutableStateOf("") }
    var sending by remember { mutableStateOf(false) }
    val scope = rememberUiScope()
    val focus = LocalFocusManager.current
    fun refine() {
        val text = request.trim()
        if (text.isEmpty() || sending || busy) return
        sending = true
        scope.launch {
            if (onRefine(text)) {
                request = ""
                focus.clearFocus() // the keyboard goes: the new version is drawn above
            }
            sending = false
        }
    }
    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            OutlinedTextField(
                request, { request = it },
                placeholder = { Text("Yêu cầu chỉnh hình, vd: vẽ thêm đường cao AH") },
                singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Send),
                keyboardActions = KeyboardActions(onSend = { refine() }),
                modifier = Modifier.weight(1f).testTag("refineField"),
            )
            IconButton(onClick = ::refine, enabled = !sending && !busy && request.isNotBlank(), modifier = Modifier.testTag("sendRefine")) {
                if (sending || busy) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                else Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Gửi yêu cầu chỉnh hình")
            }
        }
        if (requests.isNotEmpty()) {
            Text(
                "Đã yêu cầu: " + requests.joinToString(" · ") { "“$it”" },
                style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant,
            )
        }
    }
}

/** A drawing loaded with the session (images are private to their owner). */
@Composable
private fun DrawingImage(path: String, api: ApiClient) {
    var image by remember(path) { mutableStateOf(ImageStore.cached(path)) }
    LaunchedEffect(path) { if (image == null) image = ImageStore.image(path, api) }
    Box(Modifier.fillMaxWidth().height(380.dp), contentAlignment = Alignment.Center) {
        val current = image
        if (current != null) {
            var fullscreen by remember { mutableStateOf(false) }
            ZoomableImage(current, onFullscreen = { fullscreen = true })
            if (fullscreen) FullscreenImage(current) { fullscreen = false }
        } else {
            CircularProgressIndicator()
        }
    }
}

/**
 * A drawing to inspect: pinch to zoom, drag to pan, double-tap to zoom in or back, and −/+
 * buttons (web: ZoomImage.tsx). In the panel the middle button opens the drawing full screen
 * (`onFullscreen`); full screen it fits the drawing back.
 */
@Composable
fun ZoomableImage(image: Bitmap, onFullscreen: (() -> Unit)? = null, framed: Boolean = true) {
    var scale by remember(image) { mutableFloatStateOf(1f) }
    var offset by remember(image) { mutableStateOf(Offset.Zero) }
    fun zoom(to: Float) {
        scale = to.coerceIn(1f, 6f)
        if (scale == 1f) offset = Offset.Zero
    }
    val frame = if (framed) {
        Modifier
            .clip(RoundedCornerShape(14.dp))
            .border(BorderStroke(0.5.dp, MaterialTheme.colorScheme.outlineVariant), RoundedCornerShape(14.dp))
    } else {
        Modifier
    }
    Box(Modifier.fillMaxSize().then(frame).background(Color.White).testTag("drawingImage")) {
        Image(
            image.asImageBitmap(), contentDescription = "Hình vẽ", contentScale = ContentScale.Fit,
            modifier = Modifier
                .fillMaxSize()
                .clipToBounds()
                .pointerInput(image) {
                    detectTapGestures(onDoubleTap = { zoom(if (scale > 1f) 1f else 2.5f) })
                }
                .pointerInput(image) {
                    detectTransformGestures { _, pan, gesture, _ ->
                        zoom(scale * gesture)
                        if (scale > 1f) {
                            val limitX = size.width * (scale - 1) / 2
                            val limitY = size.height * (scale - 1) / 2
                            offset = Offset((offset.x + pan.x).coerceIn(-limitX, limitX), (offset.y + pan.y).coerceIn(-limitY, limitY))
                        }
                    }
                }
                .graphicsLayer {
                    scaleX = scale
                    scaleY = scale
                    translationX = offset.x
                    translationY = offset.y
                },
        )
        Surface(shape = CircleShape, color = MaterialTheme.colorScheme.surfaceContainer.copy(alpha = 0.9f), modifier = Modifier.align(Alignment.TopEnd).padding(10.dp)) {
            Row {
                IconButton(onClick = { zoom(scale / 1.5f) }) { Icon(Icons.Filled.ZoomOut, contentDescription = "Thu nhỏ") }
                if (onFullscreen != null) {
                    IconButton(onClick = onFullscreen, modifier = Modifier.testTag("fullscreenDrawing")) {
                        Icon(Icons.Filled.Fullscreen, contentDescription = "Xem toàn màn hình")
                    }
                } else {
                    IconButton(onClick = { zoom(1f) }, enabled = scale > 1f) { Icon(Icons.Filled.ZoomOutMap, contentDescription = "Vừa khung") }
                }
                IconButton(onClick = { zoom(scale * 1.5f) }) { Icon(Icons.Filled.ZoomIn, contentDescription = "Phóng to") }
            }
        }
    }
}

/** The drawing over the whole screen, zoomable, on white (the drawings are black on white). */
@Composable
private fun FullscreenImage(image: Bitmap, onClose: () -> Unit) {
    Dialog(onDismissRequest = onClose, properties = DialogProperties(usePlatformDefaultWidth = false, decorFitsSystemWindows = false)) {
        Box(Modifier.fillMaxSize().background(Color.White).testTag("fullscreenImage")) {
            Box(Modifier.fillMaxSize().safeDrawingPadding()) {
                ZoomableImage(image, onFullscreen = null, framed = false)
                Surface(
                    shape = CircleShape,
                    color = MaterialTheme.colorScheme.surfaceContainer.copy(alpha = 0.9f),
                    modifier = Modifier.align(Alignment.TopStart).padding(10.dp),
                ) {
                    IconButton(onClick = onClose, modifier = Modifier.testTag("closeFullscreen")) {
                        Icon(Icons.Filled.Close, contentDescription = "Đóng")
                    }
                }
            }
        }
    }
}

/** Shares the drawing (save it, send it in a message…). */
@Composable
private fun ShareDrawing(path: String, api: ApiClient) {
    val context = LocalContext.current
    val scope = rememberUiScope()
    IconButton(
        onClick = { scope.launch { ImageStore.image(path, api)?.let { share(context, it) } } },
        modifier = Modifier.testTag("shareDrawing"),
    ) { Icon(Icons.Filled.Share, contentDescription = "Chia sẻ hình") }
}

private suspend fun share(context: Context, image: Bitmap) {
    val file = withContext(Dispatchers.IO) {
        val dir = File(context.cacheDir, "shared").apply { mkdirs() }
        File(dir, "hinh-ve.png").also { file -> file.outputStream().use { image.compress(Bitmap.CompressFormat.PNG, 100, it) } }
    }
    val uri = FileProvider.getUriForFile(context, "${context.packageName}.files", file)
    val intent = Intent(Intent.ACTION_SEND).setType("image/png").putExtra(Intent.EXTRA_STREAM, uri).addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
    context.startActivity(Intent.createChooser(intent, "Chia sẻ hình vẽ"))
}

/** The animated drawing. The file needs the session, so it is downloaded and played locally. */
@Composable
private fun DrawingVideo(path: String, api: ApiClient) {
    val context = LocalContext.current
    var file by remember(path) { mutableStateOf<File?>(null) }
    var failed by remember(path) { mutableStateOf(false) }
    LaunchedEffect(path) {
        try {
            val data = api.file(path)
            file = withContext(Dispatchers.IO) {
                File(context.cacheDir, "mathmate-${path.hashCode().toUInt()}.mp4").also { it.writeBytes(data) }
            }
        } catch (_: ApiError) {
            failed = true
        }
    }
    Box(Modifier.fillMaxWidth().height(240.dp).clip(RoundedCornerShape(14.dp)).background(Color.Black), contentAlignment = Alignment.Center) {
        val current = file
        when {
            current != null -> {
                val player = remember(current) {
                    ExoPlayer.Builder(context).build().apply { setMediaItem(MediaItem.fromUri(current.toURI().toString())); prepare() }
                }
                androidx.compose.runtime.DisposableEffect(player) { onDispose { player.release() } }
                AndroidView(factory = { PlayerView(it).apply { this.player = player } }, modifier = Modifier.fillMaxSize())
            }
            failed -> Text("Không tải được video", color = Color.White, style = MaterialTheme.typography.bodySmall)
            else -> CircularProgressIndicator()
        }
    }
}

/**
 * The figure in the chat: a thumbnail of the latest drawing, or the progress of the one being
 * drawn. A tap opens the drawing panel.
 */
@Composable
fun FigureCard(latest: Message?, busyLabel: String?, failed: Boolean, api: ApiClient, onOpen: () -> Unit) {
    var thumbnail by remember(latest?.imageUrl) { mutableStateOf(latest?.imageUrl?.let(ImageStore::cached)) }
    LaunchedEffect(latest?.imageUrl) { latest?.imageUrl?.let { thumbnail = ImageStore.image(it, api) } }
    Surface(
        onClick = onOpen,
        shape = RoundedCornerShape(14.dp),
        color = MaterialTheme.colorScheme.surfaceContainerLow,
        modifier = Modifier.fillMaxWidth().testTag("figureCard"),
    ) {
        Row(Modifier.padding(10.dp), verticalAlignment = Alignment.CenterVertically) {
            Box(
                Modifier.size(64.dp).clip(RoundedCornerShape(10.dp)).background(Color.White).border(0.5.dp, MaterialTheme.colorScheme.outlineVariant, RoundedCornerShape(10.dp)),
                contentAlignment = Alignment.Center,
            ) {
                val current = thumbnail
                when {
                    current != null -> Image(current.asImageBitmap(), null, contentScale = ContentScale.Fit, modifier = Modifier.padding(4.dp))
                    busyLabel != null -> CircularProgressIndicator(Modifier.size(22.dp), strokeWidth = 2.dp)
                    else -> Icon(if (failed) Icons.Filled.Warning else Icons.Filled.ChangeHistory, null, tint = Color.Gray)
                }
            }
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text("Hình vẽ", style = MaterialTheme.typography.titleSmall)
                Text(
                    busyLabel ?: if (failed) "Chưa vẽ được hình" else "Chạm để xem, phóng to, chỉnh hình",
                    style = MaterialTheme.typography.labelSmall,
                    color = if (failed) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 2, overflow = TextOverflow.Ellipsis,
                )
            }
            Icon(Icons.Filled.ChevronRight, null, tint = MaterialTheme.colorScheme.outline)
        }
    }
}
