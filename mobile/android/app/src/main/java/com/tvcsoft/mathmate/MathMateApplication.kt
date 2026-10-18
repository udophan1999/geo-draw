package com.tvcsoft.mathmate

import android.app.Application
import android.content.Context
import com.agog.mathdisplay.MTFontManager
import com.tvcsoft.mathmate.core.SharedData
import com.tvcsoft.mathmate.core.api.ApiClient
import com.tvcsoft.mathmate.core.auth.CredentialStore
import com.tvcsoft.mathmate.core.auth.GuestFlag
import com.tvcsoft.mathmate.core.auth.KeystoreCredentials
import com.tvcsoft.mathmate.core.auth.MemoryCredentials
import com.tvcsoft.mathmate.core.auth.SessionStore
import com.tvcsoft.mathmate.core.chat.ChatStore
import com.tvcsoft.mathmate.core.chat.ConversationsStore
import kotlinx.coroutines.MainScope

/** The app's single instances of the API client and the stores (the iOS app's @State roots). */
class AppContainer(context: Context, testing: TestingOptions) {
    val api: ApiClient
    val session: SessionStore
    val conversations: ConversationsStore
    val chat: ChatStore
    private val scope = MainScope()

    init {
        val prefs = context.getSharedPreferences("app", Context.MODE_PRIVATE)
        // UI tests start from a clean slate and may point the app at another server.
        val credentials: CredentialStore = if (testing.active) MemoryCredentials() else KeystoreCredentials(context)
        if (testing.active) prefs.edit().remove(GUEST_MODE).apply()
        val flag = object : GuestFlag {
            override var guestMode: Boolean
                get() = prefs.getBoolean(GUEST_MODE, false)
                set(value) = prefs.edit().putBoolean(GUEST_MODE, value).apply()
        }
        api = ApiClient(testing.apiUrl ?: BuildConfig.API_BASE_URL, credentials)
        session = SessionStore(api, flag, BuildConfig.VERSION_CODE)
        conversations = ConversationsStore(api)
        chat = ChatStore(api, scope)
        // A finished turn may have renamed or created a conversation and used quota.
        chat.onTurnFinished = {
            conversations.load()
            session.refresh()
        }
    }

    private companion object {
        const val GUEST_MODE = "guest-mode"
    }
}

/** Set by the UI tests through the launch intent: `uiTesting` (credentials in memory) and `api`. */
data class TestingOptions(val active: Boolean = false, val apiUrl: String? = null)

class MathMateApplication : Application() {
    private var container: AppContainer? = null

    override fun onCreate() {
        super.onCreate()
        MTFontManager.setContext(this)
        SharedData.load(this)
    }

    /** UI tests start every test from a clean slate. */
    fun resetForTests() {
        container = null
    }

    /** Built on first use, so a UI test's launch options are known by then. */
    fun container(testing: TestingOptions): AppContainer =
        container ?: AppContainer(this, testing).also { container = it }
}
