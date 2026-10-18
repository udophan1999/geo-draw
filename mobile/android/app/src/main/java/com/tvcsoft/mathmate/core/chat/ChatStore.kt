package com.tvcsoft.mathmate.core.chat

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateMapOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.tvcsoft.mathmate.core.api.ApiClient
import com.tvcsoft.mathmate.core.api.ApiError
import com.tvcsoft.mathmate.core.api.ApiJson
import com.tvcsoft.mathmate.core.api.Conversation
import com.tvcsoft.mathmate.core.api.ConversationDetail
import com.tvcsoft.mathmate.core.api.Message
import com.tvcsoft.mathmate.core.api.TutorAction
import com.tvcsoft.mathmate.core.jobs.JobEvent
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.launch
import kotlinx.serialization.Serializable
import java.util.UUID

/** A tutor turn in progress: the student's bubble at once, then the reply as it streams. */
data class PendingTurn(
    val text: String,
    /** A JPEG of the photo sent with the message, shown until the server's copy arrives. */
    val image: ByteArray? = null,
    val label: String,
    /** The server has stored the student's message (it is in the list now). */
    val userSaved: Boolean,
    val reply: String,
)

/** A short message over the chat (web: the toasts). */
data class ChatNotice(val text: String, val isError: Boolean = false, val id: String = UUID.randomUUID().toString())

/** A photo prepared for sending: the JPEG and its size. */
class PreparedImage(val jpeg: ByteArray, val width: Int, val height: Int)

/**
 * The open conversations and their running jobs (web: lib/chat.tsx ChatProvider; iOS:
 * ChatStore). Jobs run on the server and save their results themselves; the app only follows
 * their events, and follows them again after a dropped connection (the server replays every
 * event).
 */
class ChatStore(
    private val api: ApiClient,
    private val scope: CoroutineScope,
    /** Waits between reconnections; tests make it instant. */
    private val retryDelayMillis: (attempt: Int) -> Long = { minOf(it, 5) * 1000L },
) {
    val details = mutableStateMapOf<String, ConversationDetail>()
    val pending = mutableStateMapOf<String, PendingTurn>()
    /** Conversation id → progress label of the drawing being made. */
    val figures = mutableStateMapOf<String, String>()
    val loadErrors = mutableStateMapOf<String, String>()
    var sending by mutableStateOf(false)
        private set
    var notice: ChatNotice? by mutableStateOf(null)

    /** Called when a turn changed the conversation list or the quota. */
    var onTurnFinished: (suspend () -> Unit)? = null
    /** Called when a drawing is ready (a haptic tick). */
    var onFigureDone: (() -> Unit)? = null

    private val jobs = mutableMapOf<String, Job>()

    // Conversations

    suspend fun load(id: String) {
        try {
            details[id] = api.conversation(id)
            loadErrors.remove(id)
        } catch (error: ApiError) {
            if (details[id] == null) loadErrors[id] = error.message
        }
    }

    /** Signing in or out shows someone else's conversations. */
    fun reset() {
        jobs.values.forEach { it.cancel() }
        jobs.clear()
        details.clear()
        pending.clear()
        figures.clear()
        loadErrors.clear()
    }

    // Turns

    /**
     * Sends a message or a button's action. Returns the conversation id once the server
     * accepted it (a new conversation for the first message), null after an error.
     */
    suspend fun send(
        text: String,
        image: PreparedImage? = null,
        conversationId: String? = null,
        action: TutorAction = TutorAction.ASK,
    ): String? {
        sending = true
        val started = try {
            api.sendMessage(text, conversationId, image?.jpeg, action)
        } catch (error: ApiError) {
            notice = ChatNotice(error.message, isError = true)
            return null
        } finally {
            sending = false
        }
        val id = started.conversation.id
        if (details[id] == null) details[id] = ConversationDetail(started.conversation, emptyList())
        pending[id] = PendingTurn(text, image?.jpeg, "Đang gửi...", userSaved = false, reply = "")
        follow(started.jobId, id, figure = false)
        return id
    }

    /** Edits the student's last message; the tutor's reply to it is written again. */
    suspend fun edit(conversationId: String, messageId: String, text: String): Boolean {
        val started = try {
            api.editMessage(messageId, text)
        } catch (error: ApiError) {
            notice = ChatNotice(error.message, isError = true)
            return false
        }
        // Show the edited text and drop the old reply at once; the job sends the saved versions.
        details[conversationId]?.let { detail ->
            val index = detail.messages.indexOfFirst { it.id == messageId }
            if (index >= 0) {
                val messages = detail.messages
                    .filterIndexed { offset, message -> offset <= index || message.channel != Message.Channel.CHAT }
                    .map { if (it.id == messageId) it.copy(text = text) else it }
                details[conversationId] = detail.copy(messages = messages)
            }
        }
        pending[conversationId] = PendingTurn(text, null, "Đang gửi...", userSaved = true, reply = "")
        follow(started.jobId, conversationId, figure = false)
        return true
    }

    /** Draws the figure (empty text) or refines it. */
    suspend fun drawFigure(conversationId: String, text: String = ""): Boolean = try {
        val job = api.drawFigure(conversationId, text)
        follow(job, conversationId, figure = true)
        true
    } catch (error: ApiError) {
        notice = ChatNotice(error.message, isError = true)
        false
    }

    fun isBusy(conversationId: String) = pending.containsKey(conversationId)

    // Following jobs

    private fun follow(jobId: String, id: String, figure: Boolean) {
        if (figure) figures[id] = "Đang vẽ hình..."
        jobs[jobId] = scope.launch { run(jobId, id, figure) }
    }

    private suspend fun run(jobId: String, id: String, figure: Boolean) {
        var attempts = 0
        var finished = false
        while (!finished && scope.isActive) {
            if (!figure) pending[id]?.let { pending[id] = it.copy(reply = "") } // the events start over
            try {
                api.events(jobId).collect { event -> if (handle(event, id, figure)) finished = true }
            } catch (error: CancellationException) {
                throw error
            } catch (error: ApiError) {
                if (error.status in 400..499) finished = true // the job is gone (an hour after it ended): reload instead
            }
            if (finished) break
            // Dropped (the app went to the background, the network changed): follow again.
            attempts += 1
            if (attempts > 30) break
            delay(retryDelayMillis(attempts))
        }
        jobs.remove(jobId)
        if (figure) figures.remove(id) else pending.remove(id)
        load(id)
        onTurnFinished?.invoke()
    }

    /** Applies one event; true when the job has ended. */
    private fun handle(event: JobEvent, id: String, figure: Boolean): Boolean {
        when (event.kind) {
            "message" -> decode<Message>(event.data)?.let { message ->
                upsert(message)
                if (!figure) {
                    pending[id]?.let {
                        pending[id] = if (message.role == Message.Role.USER) it.copy(userSaved = true)
                        else it.copy(reply = "", label = "") // the saved reply replaces the stream
                    }
                }
            }
            "delta" -> decode<Piece>(event.data)?.let { piece ->
                pending[id]?.let { pending[id] = it.copy(reply = it.reply + piece.text) }
            }
            "progress" -> decode<Progress>(event.data)?.let { progress ->
                if (figure) figures[id] = progress.label
                else pending[id]?.let { pending[id] = it.copy(label = progress.label) }
            }
            "conversation" -> decode<Conversation>(event.data)?.let { conversation ->
                details[id]?.let { details[id] = it.copy(conversation = conversation) }
            }
            "figure_job" -> decode<FigureJob>(event.data)?.let { job ->
                if (!jobs.containsKey(job.jobId)) follow(job.jobId, id, figure = true)
            }
            "figure_skipped" -> decode<Detail>(event.data)?.let { notice = ChatNotice("Chưa vẽ hình: ${it.detail}") }
            "failed" -> {
                notice = ChatNotice(decode<Detail>(event.data)?.detail ?: ApiError.unexpected.message, isError = true)
                return true
            }
            "done" -> {
                if (figure) onFigureDone?.invoke()
                return true
            }
        }
        return false
    }

    private fun upsert(message: Message) {
        val detail = details[message.conversationId] ?: return
        val messages = detail.messages.toMutableList()
        val index = messages.indexOfFirst { it.id == message.id }
        if (index >= 0) messages[index] = message else messages.add(message)
        details[message.conversationId] = detail.copy(messages = messages)
    }

    private inline fun <reified T> decode(data: String): T? = try {
        ApiJson.decodeFromString<T>(data)
    } catch (_: Exception) {
        null
    }

    @Serializable private data class Piece(val text: String)
    @Serializable private data class Progress(val label: String)
    @Serializable private data class FigureJob(val jobId: String)
    @Serializable private data class Detail(val detail: String)
}
