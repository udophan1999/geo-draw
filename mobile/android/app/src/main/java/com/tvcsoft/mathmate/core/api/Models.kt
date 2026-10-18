package com.tvcsoft.mathmate.core.api

import kotlinx.serialization.ExperimentalSerializationApi
import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonNamingStrategy

// The JSON shapes of api/schemas.py and api/routers/*.py (web/src/lib/api.ts and the iOS app's
// Models.swift have the same).

/** The API's JSON is snake_case; fields the app does not know are skipped. */
@OptIn(ExperimentalSerializationApi::class)
val ApiJson = Json {
    namingStrategy = JsonNamingStrategy.SnakeCase
    ignoreUnknownKeys = true
    encodeDefaults = true
    explicitNulls = false
    coerceInputValues = true
}

@Serializable
data class User(val id: String, val name: String, val role: Role = Role.USER) {
    @Serializable
    enum class Role {
        @SerialName("user") USER,
        @SerialName("admin") ADMIN,
    }
}

@Serializable
data class Quota(val used: Int, val limit: Int)

/** GET /api/auth/me; login and register answer the same, plus `token` for the app. */
@Serializable
data class Me(
    val user: User? = null,
    val quota: Quota,
    val aiAvailable: Boolean = true,
    val token: String? = null,
)

@Serializable
enum class TutorMode {
    @SerialName("hint") HINT,
    @SerialName("solution") SOLUTION,
}

@Serializable
data class Conversation(
    val id: String,
    val title: String,
    val createdAt: Double,
    val updatedAt: Double,
    val problem: String? = null,
    val mode: TutorMode = TutorMode.HINT,
    val hintLevel: Int = 1,
    /** The student reached the final answer (reported by the tutor in hint mode). */
    val solved: Boolean = false,
    val isGeometry: Boolean = false,
)

@Serializable
data class Message(
    val id: String,
    val conversationId: String,
    val role: Role,
    val text: String,
    val createdAt: Double,
    val imageUrl: String? = null,
    val videoUrl: String? = null,
    val hasDrawing: Boolean = false,
    val hasLog: Boolean = false,
    val channel: Channel = Channel.CHAT,
    val meta: Meta = Meta(),
) {
    @Serializable
    enum class Role {
        @SerialName("user") USER,
        @SerialName("assistant") ASSISTANT,
    }

    /** `chat`: the tutor conversation; `figure`: drawing requests and drawings. */
    @Serializable
    enum class Channel {
        @SerialName("chat") CHAT,
        @SerialName("figure") FIGURE,
    }

    @Serializable
    data class Meta(
        val mode: TutorMode? = null,
        val hintLevel: Int? = null,
        val solved: Boolean? = null,
        val error: Boolean? = null,
    )

    val isError: Boolean get() = meta.error == true
}

@Serializable
data class ConversationDetail(val conversation: Conversation, val messages: List<Message>)

@Serializable
data class DrawSettings(
    val mode: Mode = Mode.AI,
    val model: Model = Model.FLASH,
    val quality: Quality = Quality.M,
    val animate: Boolean = false,
) {
    @Serializable
    enum class Mode {
        @SerialName("ai") AI,
        @SerialName("parser") PARSER,
    }

    @Serializable
    enum class Model {
        @SerialName("deepseek-v4-flash") FLASH,
        @SerialName("deepseek-v4-pro") PRO,
    }

    @Serializable
    enum class Quality {
        @SerialName("l") L,
        @SerialName("m") M,
        @SerialName("h") H,
    }
}

@Serializable
data class Example(val topic: String, val name: String, val problem: String)

/** GET /api/app-config: builds below `minAndroidBuild` must update. */
@Serializable
data class AppConfig(val minAndroidBuild: Int = 0, val androidStoreUrl: String? = null)

@Serializable
data class HelpText(val markdown: String)

/** What the buttons ask the tutor for (api/routers/messages.py `action`). */
enum class TutorAction(val wire: String) { ASK("ask"), DEEPER("deeper"), SOLUTION("solution"), HINT("hint") }

/** A started turn: the conversation (new or existing) and the job to follow. */
@Serializable
data class StartedTurn(val conversation: Conversation, val jobId: String)
