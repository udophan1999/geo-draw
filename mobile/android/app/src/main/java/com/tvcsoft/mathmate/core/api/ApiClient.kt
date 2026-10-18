package com.tvcsoft.mathmate.core.api

import com.tvcsoft.mathmate.core.auth.CredentialStore
import com.tvcsoft.mathmate.core.jobs.JobEvent
import com.tvcsoft.mathmate.core.jobs.SseParser
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.flow
import kotlinx.coroutines.flow.flowOn
import kotlinx.coroutines.suspendCancellableCoroutine
import kotlinx.coroutines.withContext
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.JsonArray
import kotlinx.serialization.json.JsonObject
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.contentOrNull
import kotlinx.serialization.json.jsonObject
import kotlinx.serialization.json.jsonPrimitive
import okhttp3.Call
import okhttp3.Callback
import okhttp3.HttpUrl
import okhttp3.HttpUrl.Companion.toHttpUrl
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import okhttp3.Response
import java.io.IOException
import java.util.concurrent.TimeUnit
import kotlin.coroutines.resumeWithException

/** An error the user can read: the server's Vietnamese `detail`, or a connection problem. */
class ApiError(
    /** 0 when the server was not reached. */
    val status: Int,
    override val message: String,
    /** Free usernames offered when the chosen one is taken (409 on register). */
    val suggestions: List<String> = emptyList(),
) : Exception(message) {
    override fun equals(other: Any?) =
        other is ApiError && other.status == status && other.message == message && other.suggestions == suggestions

    override fun hashCode() = status * 31 + message.hashCode()

    companion object {
        val offline get() = ApiError(0, "Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.")
        val unexpected get() = ApiError(0, "Có lỗi xảy ra. Hãy thử lại.")
    }
}

/**
 * The FastAPI server in api/, as the app calls it: every request says `X-Client: android`,
 * carries the session token as `Authorization: Bearer` and the guest id as `X-Guest-Id`
 * (api/deps.py). The iOS app's APIClient does the same.
 */
class ApiClient(
    val baseUrl: HttpUrl,
    private val credentials: CredentialStore,
    client: OkHttpClient = defaultClient,
) {
    constructor(baseUrl: String, credentials: CredentialStore, client: OkHttpClient = defaultClient) :
        this(baseUrl.toHttpUrl(), credentials, client)

    private val http = client
    /** Server-sent events stay open while a job runs; keep-alives arrive every 15 s. */
    private val streaming = client.newBuilder().readTimeout(60, TimeUnit.SECONDS).callTimeout(0, TimeUnit.SECONDS).build()
    /** A photo upload on a slow network. */
    private val uploading = client.newBuilder().writeTimeout(120, TimeUnit.SECONDS).readTimeout(120, TimeUnit.SECONDS).build()

    val isSignedIn: Boolean get() = credentials.token != null

    // Requests

    /** A request with the app's headers; `path` is relative to `/api/`. */
    fun request(path: String): Request.Builder = requestFor(baseUrl.resolve("api/$path")!!)

    private fun requestFor(url: HttpUrl): Request.Builder {
        val builder = Request.Builder().url(url).header("X-Client", "android")
        credentials.token?.let { builder.header("Authorization", "Bearer $it") }
        credentials.guestId?.let { builder.header("X-Guest-Id", it) }
        return builder
    }

    /** Sends a request and checks the answer; returns the body. */
    suspend fun send(request: Request, client: OkHttpClient = http): ByteArray {
        val response = try {
            client.newCall(request).await()
        } catch (error: IOException) {
            throw ApiError.offline
        }
        return response.use {
            // A new guest id comes back in a header the first time (api/main.py).
            it.header("X-Guest-Id")?.let { id -> credentials.guestId = id }
            val body = withContext(Dispatchers.IO) {
                try {
                    it.body?.bytes() ?: ByteArray(0)
                } catch (error: IOException) {
                    throw ApiError.offline
                }
            }
            if (!it.isSuccessful) throw error(it.code, body)
            body
        }
    }

    suspend inline fun <reified T> get(path: String): T = decode(send(request(path).get().build()))

    suspend inline fun <reified B, reified T> send(path: String, method: String, body: B): T =
        decode(send(jsonRequest(path, method, ApiJson.encodeToString(body))))

    suspend inline fun <reified B> sendOnly(path: String, method: String, body: B) {
        send(jsonRequest(path, method, ApiJson.encodeToString(body)))
    }

    fun jsonRequest(path: String, method: String, json: String): Request =
        request(path).method(method, json.toRequestBody(JSON)).build()

    inline fun <reified T> decode(data: ByteArray): T = try {
        ApiJson.decodeFromString(data.decodeToString())
    } catch (error: Exception) {
        throw ApiError.unexpected
    }

    // Accounts

    suspend fun me(): Me = get("auth/me")

    suspend fun login(username: String, password: String): Me = signIn("auth/login", username, password)

    suspend fun register(username: String, password: String): Me = signIn("auth/register", username, password)

    private suspend fun signIn(path: String, username: String, password: String): Me {
        val me: Me = send(path, "POST", Credentials(username, password))
        credentials.token = me.token
        return me
    }

    /** Ends the session on the server too; the token is forgotten even when offline. */
    suspend fun logout() {
        try {
            send(request("auth/logout").post(EMPTY).build())
        } catch (_: ApiError) {
        } finally {
            credentials.token = null
        }
    }

    suspend fun deleteAccount(password: String) {
        sendOnly("auth/me", "DELETE", Confirmation(password))
        credentials.token = null
    }

    // App data

    suspend fun appConfig(): AppConfig = get("app-config")
    suspend fun settings(): DrawSettings = get("settings")
    suspend fun saveSettings(settings: DrawSettings): DrawSettings = send("settings", "PUT", settings)
    suspend fun help(): String = get<HelpText>("help").markdown
    suspend fun examples(): List<Example> = get("examples")

    // Conversations

    suspend fun conversations(): List<Conversation> = get("conversations")
    suspend fun conversation(id: String): ConversationDetail = get("conversations/$id")
    suspend fun rename(id: String, title: String): Conversation = send("conversations/$id", "PATCH", Title(title))
    suspend fun deleteConversation(id: String) {
        send(request("conversations/$id").delete().build())
    }

    // Turns

    /** A message to the tutor (POST /api/messages, multipart). `image` is JPEG data. */
    suspend fun sendMessage(text: String, conversationId: String?, image: ByteArray?, action: TutorAction): StartedTurn {
        val form = MultipartBody.Builder().setType(MultipartBody.FORM).addFormDataPart("text", text)
        conversationId?.let { form.addFormDataPart("conversation_id", it) }
        if (action != TutorAction.ASK) form.addFormDataPart("action", action.wire)
        image?.let { form.addFormDataPart("image", "de-bai.jpg", it.toRequestBody(JPEG)) }
        return decode(send(request("messages").post(form.build()).build(), uploading))
    }

    /** Edit the student's last message; the tutor answers it again (one AI turn). */
    suspend fun editMessage(id: String, text: String): StartedTurn = send("messages/$id", "PATCH", Text(text))

    /** Draw the figure (empty text) or refine it with a request; returns the job id. */
    suspend fun drawFigure(conversationId: String, text: String = ""): String =
        send<Text, Job>("conversations/$conversationId/figure", "POST", Text(text)).jobId

    /**
     * A file the API serves at an absolute path such as `/api/messages/…/image?v=…`; images
     * need the session, so they are loaded here rather than by an image library.
     */
    suspend fun file(path: String): ByteArray {
        val url = baseUrl.resolve(path) ?: throw ApiError.unexpected
        return send(requestFor(url).get().build(), uploading)
    }

    /**
     * The job's server-sent events, as they arrive. Ends after `done` or `failed`, or when the
     * connection drops (the caller may then follow it again: the server replays them all).
     */
    fun events(jobId: String): Flow<JobEvent> = flow {
        val call = streaming.newCall(request("jobs/$jobId/events").header("Accept", "text/event-stream").get().build())
        val response = try {
            call.execute()
        } catch (error: IOException) {
            throw ApiError.offline
        }
        response.use {
            if (!it.isSuccessful) throw error(it.code, it.body?.bytes() ?: ByteArray(0))
            val source = it.body?.source() ?: return@use
            val parser = SseParser()
            try {
                while (true) {
                    val line = source.readUtf8Line() ?: break
                    parser.feed(line.trimEnd('\r'))?.let { event -> emit(event) }
                }
            } catch (error: IOException) {
                throw ApiError.offline
            }
        }
    }.flowOn(Dispatchers.IO)

    @Serializable private data class Credentials(val username: String, val password: String)
    @Serializable private data class Confirmation(val password: String)
    @Serializable private data class Title(val title: String)
    @Serializable private data class Text(val text: String)
    @Serializable private data class Job(val jobId: String)

    companion object {
        private val JSON = "application/json".toMediaType()
        private val JPEG = "image/jpeg".toMediaType()
        private val EMPTY: RequestBody = ByteArray(0).toRequestBody(null)

        val defaultClient: OkHttpClient = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .build()

        /**
         * FastAPI errors: `{"detail": "…"}`, validation errors `{"detail": [{"msg": "…"}]}`, and
         * register's `{"detail": "…", "suggestions": [...]}`.
         */
        fun error(status: Int, body: ByteArray): ApiError {
            val json = try {
                ApiJson.parseToJsonElement(body.decodeToString()) as? JsonObject
            } catch (_: Exception) {
                null
            }
            val detail = json?.get("detail")
            val message = when (detail) {
                is JsonPrimitive -> detail.contentOrNull
                is JsonArray -> detail.firstOrNull()?.jsonObject?.get("msg")?.jsonPrimitive?.contentOrNull
                else -> null
            } ?: ApiError.unexpected.message
            val suggestions = (json?.get("suggestions") as? JsonArray)?.mapNotNull { it.jsonPrimitive.contentOrNull }.orEmpty()
            return ApiError(status, message, suggestions)
        }
    }
}

/** OkHttp's callback API as a suspending call that cancels the request when cancelled. */
private suspend fun Call.await(): Response = suspendCancellableCoroutine { continuation ->
    enqueue(object : Callback {
        override fun onResponse(call: Call, response: Response) {
            continuation.resume(response) { _, value, _ -> value.close() }
        }

        override fun onFailure(call: Call, e: IOException) {
            continuation.resumeWithException(e)
        }
    })
    continuation.invokeOnCancellation { cancel() }
}
