package com.tvcsoft.mathmate.core.chat

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.tvcsoft.mathmate.core.api.ApiClient
import com.tvcsoft.mathmate.core.api.ApiError
import com.tvcsoft.mathmate.core.api.Conversation

/** The conversation list (web: the Sidebar's query), kept in memory while the app runs. */
class ConversationsStore(private val api: ApiClient) {
    var items: List<Conversation> by mutableStateOf(emptyList())
        private set
    var loaded by mutableStateOf(false)
        private set
    var error: String? by mutableStateOf(null)

    suspend fun load() {
        try {
            items = api.conversations()
            error = null
        } catch (failure: ApiError) {
            error = failure.message
        }
        loaded = true
    }

    suspend fun rename(conversation: Conversation, title: String) {
        val trimmed = title.trim()
        if (trimmed.isEmpty() || trimmed == conversation.title) return
        try {
            val renamed = api.rename(conversation.id, trimmed)
            items = items.map { if (it.id == renamed.id) renamed else it }
        } catch (failure: ApiError) {
            error = failure.message
        }
    }

    suspend fun delete(conversation: Conversation) {
        val before = items
        items = items.filter { it.id != conversation.id } // at once; put back if the server refuses
        try {
            api.deleteConversation(conversation.id)
        } catch (failure: ApiError) {
            items = before
            error = failure.message
        }
    }

    /** Signing in or out shows someone else's list. */
    fun reset() {
        items = emptyList()
        loaded = false
        error = null
    }
}
