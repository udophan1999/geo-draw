package com.tvcsoft.mathmate.core.auth

import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import com.tvcsoft.mathmate.core.api.ApiClient
import com.tvcsoft.mathmate.core.api.ApiError
import com.tvcsoft.mathmate.core.api.Me
import com.tvcsoft.mathmate.core.api.User

/** The "Dùng thử" choice, kept between launches (web: lib/guest.ts in localStorage). */
interface GuestFlag {
    var guestMode: Boolean
}

class MemoryGuestFlag(override var guestMode: Boolean = false) : GuestFlag

/**
 * Who is using the app and which screen they may see. Mirrors the web's AppLayout guard and
 * the iOS SessionStore: without an account, the app opens on the welcome screen unless the
 * student chose "Dùng thử" before.
 */
class SessionStore(
    val api: ApiClient,
    private val flag: GuestFlag,
    /** This build's versionCode, compared with the server's `min_android_build`. */
    private val build: Int,
) {
    sealed interface Phase {
        data object Loading : Phase
        /** This build is older than the server's `min_android_build`. */
        data class UpdateRequired(val storeUrl: String?) : Phase
        data object Welcome : Phase
        data object Ready : Phase
    }

    var phase: Phase by mutableStateOf(Phase.Loading)
        private set
    var me: Me? by mutableStateOf(null)
        private set
    /** Shown on the welcome screen when the server could not be reached at launch. */
    var startError: String? by mutableStateOf(null)
        private set

    val user: User? get() = me?.user
    val isGuest: Boolean get() = me?.user == null

    suspend fun start() {
        phase = Phase.Loading
        startError = null
        val config = try {
            api.appConfig()
        } catch (_: ApiError) {
            null
        }
        if (config != null && build < config.minAndroidBuild) {
            phase = Phase.UpdateRequired(config.androidStoreUrl)
            return
        }
        try {
            me = api.me()
            if (me?.user == null && api.isSignedIn) {
                api.logout() // the session ended on the server (expired, account locked…)
            }
        } catch (error: ApiError) {
            startError = error.message
        }
        phase = if (me != null && (me?.user != null || flag.guestMode)) Phase.Ready else Phase.Welcome
    }

    suspend fun refresh() {
        try {
            me = api.me()
        } catch (_: ApiError) {
        }
    }

    suspend fun login(username: String, password: String) {
        me = api.login(username, password)
        flag.guestMode = false
        phase = Phase.Ready
    }

    suspend fun register(username: String, password: String) {
        me = api.register(username, password)
        flag.guestMode = false
        phase = Phase.Ready
    }

    suspend fun continueAsGuest() {
        flag.guestMode = true
        if (me == null) refresh()
        phase = if (me == null) Phase.Welcome else Phase.Ready
    }

    /** A guest who wants to sign in: back to the welcome screen, keeping the guest id. */
    fun showWelcome() {
        flag.guestMode = false
        phase = Phase.Welcome
    }

    suspend fun logout() {
        api.logout()
        flag.guestMode = false
        me = null
        refresh()
        phase = Phase.Welcome
    }

    suspend fun deleteAccount(password: String) {
        api.deleteAccount(password)
        flag.guestMode = false
        me = null
        refresh()
        phase = Phase.Welcome
    }
}
