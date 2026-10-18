package com.tvcsoft.mathmate

import com.tvcsoft.mathmate.core.api.ApiClient
import com.tvcsoft.mathmate.core.api.ApiError
import com.tvcsoft.mathmate.core.auth.MemoryCredentials
import com.tvcsoft.mathmate.core.auth.MemoryGuestFlag
import com.tvcsoft.mathmate.core.auth.SessionStore
import com.tvcsoft.mathmate.core.chat.ChatStore
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.runBlocking
import kotlinx.coroutines.withTimeout
import okhttp3.mockwebserver.Dispatcher
import okhttp3.mockwebserver.MockResponse
import okhttp3.mockwebserver.MockWebServer
import okhttp3.mockwebserver.RecordedRequest
import org.junit.After
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertNull
import org.junit.Assert.assertTrue
import org.junit.Assert.fail
import org.junit.Before
import org.junit.Test
import java.util.concurrent.ConcurrentLinkedQueue
import java.util.concurrent.CopyOnWriteArrayList

private const val ME = """{"user":{"id":"u1","name":"An 7A","role":"user"},"quota":{"used":1,"limit":100},"ai_available":true}"""
private const val GUEST_ME = """{"user":null,"quota":{"used":0,"limit":10},"ai_available":true}"""

/** A fake API: answers by path, several queued answers per path play in turn (the last repeats). */
class FakeApi {
    val server = MockWebServer()
    val requests = CopyOnWriteArrayList<RecordedRequest>()
    private val answers = mutableMapOf<String, ConcurrentLinkedQueue<MockResponse>>()

    fun reply(path: String, json: String, status: Int = 200, headers: Map<String, String> = emptyMap()) {
        val response = MockResponse().setResponseCode(status).setBody(json).setHeader("Content-Type", "application/json")
        headers.forEach { (name, value) -> response.setHeader(name, value) }
        answers.getOrPut(path) { ConcurrentLinkedQueue() }.add(response)
    }

    fun events(path: String, body: String) {
        answers.getOrPut(path) { ConcurrentLinkedQueue() }
            .add(MockResponse().setBody(body).setHeader("Content-Type", "text/event-stream"))
    }

    fun start() {
        server.dispatcher = object : Dispatcher() {
            override fun dispatch(request: RecordedRequest): MockResponse {
                requests.add(request)
                val queue = answers[request.requestUrl!!.encodedPath] ?: return MockResponse().setResponseCode(404).setBody("""{"detail":"Not Found"}""")
                return if (queue.size > 1) queue.poll()!! else queue.peek()!!
            }
        }
        server.start()
    }

    fun client(credentials: MemoryCredentials = MemoryCredentials()) = ApiClient(server.url("/").toString(), credentials)

    fun path(request: RecordedRequest) = request.requestUrl!!.encodedPath
}

class ApiClientTest {
    private val api = FakeApi()

    @Before fun setUp() = api.start()
    @After fun tearDown() = api.server.shutdown()

    @Test
    fun everyRequestSaysItIsTheAppAndCarriesItsIds() = runBlocking {
        api.reply("/api/auth/me", ME)
        api.client(MemoryCredentials(token = "tok", guestId = "a1b2")).me()
        val request = api.requests.last()
        assertEquals("android", request.getHeader("X-Client"))
        assertEquals("Bearer tok", request.getHeader("Authorization"))
        assertEquals("a1b2", request.getHeader("X-Guest-Id"))
        assertEquals("/api/auth/me", api.path(request))
    }

    @Test
    fun aNewGuestIdIsRemembered() = runBlocking {
        api.reply("/api/auth/me", GUEST_ME, headers = mapOf("X-Guest-Id" to "0123456789abcdef01234567"))
        val credentials = MemoryCredentials()
        val answer = api.client(credentials).me()
        assertNull(answer.user)
        assertEquals(10, answer.quota.limit)
        assertEquals("0123456789abcdef01234567", credentials.guestId)
        assertNull(credentials.token)
    }

    @Test
    fun loginKeepsTheTokenAndLogoutForgetsItEvenOffline() = runBlocking {
        api.reply("/api/auth/login", ME.dropLast(1) + ""","token":"secret"}""")
        val credentials = MemoryCredentials()
        val client = api.client(credentials)
        assertEquals("An 7A", client.login("An 7A", "hinhhoc1").user?.name)
        assertEquals("secret", credentials.token)
        assertTrue(api.requests.last().body.readUtf8().contains(""""username":"An 7A""""))

        api.server.shutdown()
        client.logout()
        assertNull(credentials.token)
    }

    @Test
    fun serverErrorsKeepTheirVietnameseMessage() = runBlocking {
        api.reply("/api/auth/login", """{"detail":"Sai tên đăng nhập hoặc mật khẩu."}""", status = 401)
        api.reply("/api/auth/register", """{"detail":"Tên đăng nhập «an» đã có người dùng.","suggestions":["an 2","an 3","an 4"]}""", status = 409)
        val client = api.client()
        try {
            client.login("an", "sai")
            fail("login should fail")
        } catch (error: ApiError) {
            assertEquals(ApiError(401, "Sai tên đăng nhập hoặc mật khẩu."), error)
        }
        try {
            client.register("an", "hinhhoc1")
            fail("register should fail")
        } catch (error: ApiError) {
            assertEquals(409, error.status)
            assertEquals(listOf("an 2", "an 3", "an 4"), error.suggestions)
        }
    }

    @Test
    fun validationErrorsAndOfflineHaveReadableMessages() = runBlocking {
        assertEquals("Trường bắt buộc", ApiClient.error(422, """{"detail":[{"msg":"Trường bắt buộc"}]}""".toByteArray()).message)
        assertEquals(ApiError(500, ApiError.unexpected.message), ApiClient.error(500, "oops".toByteArray()))
        val client = api.client()
        api.server.shutdown()
        try {
            client.me()
            fail("me should fail offline")
        } catch (error: ApiError) {
            assertEquals(ApiError.offline, error)
        }
    }

    @Test
    fun conversationsDecodeFromSnakeCase() = runBlocking {
        api.reply(
            "/api/conversations",
            """[{"id":"c1","title":"Phương trình","created_at":1.5,"updated_at":2.5,"problem":"x+1=3","mode":"hint","hint_level":2,"solved":false,"is_geometry":false}]""",
        )
        val list = api.client().conversations()
        assertEquals(2, list.first().hintLevel)
        assertFalse(list.first().isGeometry)
    }
}

class SessionStoreTest {
    private val api = FakeApi()

    @Before fun setUp() = api.start()
    @After fun tearDown() = api.server.shutdown()

    private fun store(credentials: MemoryCredentials = MemoryCredentials(), flag: MemoryGuestFlag = MemoryGuestFlag()) =
        SessionStore(api.client(credentials), flag, build = 1)

    @Test
    fun aSignedInUserGoesStraightIn() = runBlocking {
        api.reply("/api/app-config", """{"min_android_build":0,"android_store_url":null}""")
        api.reply("/api/auth/me", ME)
        val session = store(MemoryCredentials(token = "tok"))
        session.start()
        assertEquals(SessionStore.Phase.Ready, session.phase)
        assertEquals("An 7A", session.user?.name)
    }

    @Test
    fun withoutAnAccountTheWelcomeScreenComesFirstUntilTheGuestChoice() = runBlocking {
        api.reply("/api/auth/me", GUEST_ME)
        val flag = MemoryGuestFlag()
        val session = store(flag = flag)
        session.start()
        assertEquals(SessionStore.Phase.Welcome, session.phase)
        session.continueAsGuest()
        assertEquals(SessionStore.Phase.Ready, session.phase)
        assertTrue(session.isGuest)

        val again = store(flag = flag)
        again.start()
        assertEquals("the guest choice is remembered", SessionStore.Phase.Ready, again.phase)
    }

    @Test
    fun anEndedSessionIsForgotten() = runBlocking {
        api.reply("/api/auth/me", GUEST_ME)
        val credentials = MemoryCredentials(token = "expired")
        val session = store(credentials)
        session.start()
        assertEquals(SessionStore.Phase.Welcome, session.phase)
        assertNull(credentials.token)
    }

    @Test
    fun anOldBuildMustUpdate() = runBlocking {
        api.reply("/api/app-config", """{"min_ios_build":0,"min_android_build":999999,"android_store_url":"https://play.google.com/store/apps/details?id=com.tvcsoft.mathmate"}""")
        val session = store()
        session.start()
        assertEquals(SessionStore.Phase.UpdateRequired("https://play.google.com/store/apps/details?id=com.tvcsoft.mathmate"), session.phase)
    }

    @Test
    fun offlineAtLaunchShowsTheWelcomeScreenWithAMessage() = runBlocking {
        val session = store()
        api.server.shutdown()
        session.start()
        assertEquals(SessionStore.Phase.Welcome, session.phase)
        assertEquals(ApiError.offline.message, session.startError)
    }
}

class ChatStoreTest {
    private val api = FakeApi()
    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.Default)

    @Before fun setUp() = api.start()

    @After
    fun tearDown() {
        scope.cancel()
        api.server.shutdown()
    }

    companion object {
        const val CONVERSATION = """{"id":"c1","title":"Phương trình","created_at":1,"updated_at":2,"problem":"x+1=3","mode":"hint","hint_level":1,"solved":false,"is_geometry":false}"""
        fun message(id: String, role: String, text: String) =
            """{"id":"$id","conversation_id":"c1","role":"$role","text":"$text","created_at":1,"image_url":null,"video_url":null,"has_drawing":false,"has_log":false,"channel":"chat","meta":{}}"""

        val EVENTS = """
            |event: message
            |data: ${message("m1", "user", "x+1=3")}
            |
            |event: progress
            |data: {"stage":"tutor","label":"Gia sư đang suy nghĩ..."}
            |
            |event: delta
            |data: {"text":"Em thử "}
            |
            |event: delta
            |data: {"text":"chuyển vế nhé."}
            |
            |event: message
            |data: ${message("m2", "assistant", "Em thử chuyển vế nhé.")}
            |
            |event: conversation
            |data: ${CONVERSATION.replace("\"hint_level\":1", "\"hint_level\":2")}
            |
            |event: done
            |data: {}
            |
            |
        """.trimMargin()
    }

    private fun store(): ChatStore {
        api.reply("/api/messages", """{"conversation":$CONVERSATION,"job_id":"j1"}""")
        api.reply(
            "/api/conversations/c1",
            """{"conversation":${CONVERSATION.replace("\"hint_level\":1", "\"hint_level\":2")},"messages":[${message("m1", "user", "x+1=3")},${message("m2", "assistant", "Em thử chuyển vế nhé.")}]}""",
        )
        return ChatStore(api.client(), scope, retryDelayMillis = { 10 })
    }

    private suspend fun waitUntilIdle(chat: ChatStore, finished: () -> Boolean) = withTimeout(5000) {
        while (!finished()) delay(20)
    }

    @Test
    fun aTurnStreamsThenSavesTheReply() = runBlocking {
        api.events("/api/jobs/j1/events", EVENTS)
        val chat = store()
        var finished = 0
        chat.onTurnFinished = { finished += 1 }
        val id = chat.send("x+1=3")
        assertEquals("c1", id)
        assertEquals("x+1=3", chat.pending["c1"]?.text)
        waitUntilIdle(chat) { finished == 1 }
        assertNull(chat.pending["c1"])
        val detail = chat.details.getValue("c1")
        assertEquals(listOf("m1", "m2"), detail.messages.map { it.id })
        assertEquals(2, detail.conversation.hintLevel)
        val sent = api.requests.first { api.path(it) == "/api/messages" }.body.readUtf8()
        assertTrue(sent, sent.contains("name=\"text\"\r\nContent-Length: 5\r\n\r\nx+1=3"))
    }

    @Test
    fun aDroppedStreamIsFollowedAgainWithoutDoublingTheReply() = runBlocking {
        // The first connection drops after one piece; the server replays everything after.
        val dropped = EVENTS.split("event: delta")[0] + "event: delta\ndata: {\"text\":\"Em thử \"}\n\n"
        api.events("/api/jobs/j1/events", dropped)
        api.events("/api/jobs/j1/events", EVENTS)
        val chat = store()
        var finished = false
        chat.onTurnFinished = { finished = true }
        chat.send("x+1=3")
        waitUntilIdle(chat) { finished }
        assertEquals(2, api.requests.count { api.path(it) == "/api/jobs/j1/events" })
        assertEquals(listOf("x+1=3", "Em thử chuyển vế nhé."), chat.details["c1"]?.messages?.map { it.text })
    }

    @Test
    fun aRefusedMessageShowsTheServerReason() = runBlocking {
        api.reply("/api/messages", """{"detail":"Bạn đã dùng hết 10 lượt dùng AI hôm nay."}""", status = 429)
        val chat = ChatStore(api.client(), scope)
        assertNull(chat.send("x+1=3"))
        assertEquals("Bạn đã dùng hết 10 lượt dùng AI hôm nay.", chat.notice?.text)
        assertTrue(chat.notice?.isError == true)
    }
}
