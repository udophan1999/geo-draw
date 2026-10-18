package com.tvcsoft.mathmate.ui

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import com.tvcsoft.mathmate.ui.common.rememberUiScope
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.compose.LifecycleEventEffect
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.tvcsoft.mathmate.AppContainer
import com.tvcsoft.mathmate.core.auth.SessionStore
import com.tvcsoft.mathmate.ui.auth.WelcomeScreen
import com.tvcsoft.mathmate.ui.chat.ChatScreen
import com.tvcsoft.mathmate.ui.conversations.ConversationListScreen
import com.tvcsoft.mathmate.ui.settings.SettingsScreen
import com.tvcsoft.mathmate.ui.theme.Brand
import kotlinx.coroutines.launch

/** Which screen the student may see (web: the AppLayout guard; iOS: RootView). */
@Composable
fun MathMateRoot(container: AppContainer) {
    val session = container.session
    LaunchedEffect(Unit) { session.start() }
    // Signing in or out shows someone else's conversations.
    LaunchedEffect(session.user?.id) {
        container.conversations.reset()
        container.chat.reset()
    }
    Surface(color = MaterialTheme.colorScheme.background, modifier = Modifier.fillMaxSize()) {
        when (val phase = session.phase) {
            SessionStore.Phase.Loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) { CircularProgressIndicator() }
            is SessionStore.Phase.UpdateRequired -> UpdateRequired(phase.storeUrl)
            SessionStore.Phase.Welcome -> WelcomeScreen(session)
            SessionStore.Phase.Ready -> Main(container)
        }
    }
}

/** The list, a conversation and the settings. */
@Composable
private fun Main(container: AppContainer) {
    val navigation = rememberNavController()
    val scope = rememberUiScope()
    // The conversation on screen, for reloading it when the app comes back.
    var open by remember { mutableStateOf<String?>(null) }
    // Back from the background: jobs that ended meanwhile are on the server.
    LifecycleEventEffect(Lifecycle.Event.ON_RESUME) {
        scope.launch {
            container.conversations.load()
            open?.let { container.chat.load(it) }
        }
    }
    NavHost(navigation, startDestination = "list") {
        composable("list") {
            LaunchedEffect(Unit) { open = null }
            ConversationListScreen(
                container.session, container.conversations,
                onOpen = { navigation.navigate("chat?id=$it") },
                onNew = { navigation.navigate("chat") },
                onSettings = { navigation.navigate("settings") },
            )
        }
        composable("chat?id={id}", arguments = listOf(navArgument("id") { type = NavType.StringType; nullable = true })) { entry ->
            // A new conversation gets its id from the first message; the screen stays (as the
            // iOS app changes its selection), so the streaming reply is not interrupted.
            var id by rememberSaveable { mutableStateOf(entry.arguments?.getString("id")) }
            LaunchedEffect(id) { open = id }
            ChatScreen(
                container, id,
                onBack = { navigation.popBackStack() },
                onCreated = { created ->
                    id = created
                    scope.launch { container.conversations.load() }
                },
            )
        }
        composable("settings") { SettingsScreen(container.session) { navigation.popBackStack() } }
    }
}

/** This build is too old for the server (GET /api/app-config). */
@Composable
private fun UpdateRequired(storeUrl: String?) {
    val context = LocalContext.current
    Column(
        Modifier.fillMaxSize().padding(32.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.spacedBy(12.dp, Alignment.CenterVertically),
    ) {
        Text("Cập nhật ${Brand.APP_NAME}", style = MaterialTheme.typography.headlineSmall)
        Text(
            "Phiên bản này đã cũ. Hãy cập nhật để tiếp tục học cùng ${Brand.APP_NAME}.",
            textAlign = TextAlign.Center, color = MaterialTheme.colorScheme.onSurfaceVariant,
        )
        if (storeUrl != null) {
            Button(onClick = { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(storeUrl))) }) { Text("Mở Google Play") }
        }
    }
}
