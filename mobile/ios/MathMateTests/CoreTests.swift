import Foundation
import Testing
@testable import MathMate

private let me = #"{"user":{"id":"u1","name":"An 7A","role":"user"},"quota":{"used":1,"limit":100},"ai_available":true}"#
private let guestMe = #"{"user":null,"quota":{"used":0,"limit":10},"ai_available":true}"#

private func client(_ credentials: MemoryCredentials = MemoryCredentials()) -> APIClient {
    APIClient(baseURL: URL(string: "http://test.local")!, credentials: credentials, session: StubProtocol.session())
}

/// The stub's state is shared, so every suite that uses it runs inside this one, one test at a time.
@Suite(.serialized)
enum Stubbed {}

extension Stubbed {
@Suite
struct APIClientTests {
    init() { StubProtocol.reset() }

    @Test func everyRequestSaysItIsTheAppAndCarriesItsIDs() async throws {
        StubProtocol.reply("/api/auth/me", json: me)
        _ = try await client(MemoryCredentials(token: "tok", guestID: "a1b2")).me()
        let request = try #require(StubProtocol.requests.last)
        #expect(request.value(forHTTPHeaderField: "X-Client") == "ios")
        #expect(request.value(forHTTPHeaderField: "Authorization") == "Bearer tok")
        #expect(request.value(forHTTPHeaderField: "X-Guest-Id") == "a1b2")
        #expect(request.url?.absoluteString == "http://test.local/api/auth/me")
    }

    @Test func aNewGuestIDIsRemembered() async throws {
        StubProtocol.reply("/api/auth/me", json: guestMe, headers: ["X-Guest-Id": "0123456789abcdef01234567"])
        let credentials = MemoryCredentials()
        let answer = try await client(credentials).me()
        #expect(answer.user == nil && answer.quota.limit == 10)
        #expect(credentials.guestID == "0123456789abcdef01234567")
        #expect(credentials.token == nil)
    }

    @Test func loginKeepsTheTokenAndLogoutForgetsItEvenOffline() async throws {
        StubProtocol.reply("/api/auth/login", json: me.dropLast() + #","token":"secret"}"#)
        let credentials = MemoryCredentials()
        let api = client(credentials)
        let answer = try await api.login(username: "An 7A", password: "hinhhoc1")
        #expect(answer.user?.name == "An 7A")
        #expect(credentials.token == "secret")
        let body = try #require(StubProtocol.requests.last?.httpBody)
        #expect(String(decoding: body, as: UTF8.self).contains(#""username":"An 7A""#))

        StubProtocol.offline = true
        await api.logout()
        #expect(credentials.token == nil)
    }

    @Test func serverErrorsKeepTheirVietnameseMessage() async throws {
        StubProtocol.reply("/api/auth/login", status: 401, json: #"{"detail":"Sai tên đăng nhập hoặc mật khẩu."}"#)
        StubProtocol.reply("/api/auth/register", status: 409,
                           json: #"{"detail":"Tên đăng nhập «an» đã có người dùng.","suggestions":["an 2","an 3","an 4"]}"#)
        let api = client()
        await #expect(throws: APIError(status: 401, message: "Sai tên đăng nhập hoặc mật khẩu.")) {
            try await api.login(username: "an", password: "sai")
        }
        do {
            _ = try await api.register(username: "an", password: "hinhhoc1")
            Issue.record("register should fail")
        } catch let error as APIError {
            #expect(error.status == 409)
            #expect(error.suggestions == ["an 2", "an 3", "an 4"])
        }
    }

    @Test func validationErrorsAndOfflineHaveReadableMessages() async throws {
        let validation = APIClient.error(status: 422, body: Data(#"{"detail":[{"msg":"Trường bắt buộc"}]}"#.utf8))
        #expect(validation.message == "Trường bắt buộc")
        #expect(APIClient.error(status: 500, body: Data("oops".utf8)) == APIError(status: 500, message: APIError.unexpected.message))
        StubProtocol.offline = true
        await #expect(throws: APIError.offline) { try await client().me() }
    }

    @Test func conversationsDecodeFromSnakeCase() async throws {
        StubProtocol.reply("/api/conversations", json: #"""
            [{"id":"c1","title":"Phương trình","created_at":1.5,"updated_at":2.5,"problem":"x+1=3",
              "mode":"hint","hint_level":2,"solved":false,"is_geometry":false}]
            """#)
        let list = try await client().conversations()
        #expect(list.first?.hintLevel == 2)
        #expect(list.first?.isGeometry == false)
    }
}

@Suite
@MainActor
struct SessionStoreTests {
    init() { StubProtocol.reset() }

    private func store(_ credentials: MemoryCredentials = MemoryCredentials()) -> (SessionStore, UserDefaults) {
        let defaults = UserDefaults(suiteName: "test-\(UUID().uuidString)")!
        return (SessionStore(api: client(credentials), defaults: defaults), defaults)
    }

    @Test func aSignedInUserGoesStraightIn() async {
        StubProtocol.reply("/api/app-config", json: #"{"min_ios_build":0,"ios_store_url":null}"#)
        StubProtocol.reply("/api/auth/me", json: me)
        let (session, _) = store(MemoryCredentials(token: "tok"))
        await session.start()
        #expect(session.phase == .ready)
        #expect(session.user?.name == "An 7A")
    }

    @Test func withoutAnAccountTheWelcomeScreenComesFirstUntilTheGuestChoice() async {
        StubProtocol.reply("/api/auth/me", json: guestMe)
        let (session, defaults) = store()
        await session.start()
        #expect(session.phase == .welcome)
        await session.continueAsGuest()
        #expect(session.phase == .ready)
        #expect(session.isGuest)

        let (again, _) = (SessionStore(api: client(), defaults: defaults), ())
        await again.start()
        #expect(again.phase == .ready, "the guest choice is remembered")
    }

    @Test func anEndedSessionIsForgotten() async {
        StubProtocol.reply("/api/auth/me", json: guestMe)
        let credentials = MemoryCredentials(token: "expired")
        let (session, _) = store(credentials)
        await session.start()
        #expect(session.phase == .welcome)
        #expect(credentials.token == nil)
    }

    @Test func anOldBuildMustUpdate() async {
        StubProtocol.reply("/api/app-config",
                           json: #"{"min_ios_build":999999,"ios_store_url":"https://apps.apple.com/app/id1"}"#)
        let (session, _) = store()
        await session.start()
        #expect(session.phase == .updateRequired(storeURL: URL(string: "https://apps.apple.com/app/id1")))
    }

    @Test func offlineAtLaunchShowsTheWelcomeScreenWithAMessage() async {
        StubProtocol.offline = true
        let (session, _) = store()
        await session.start()
        #expect(session.phase == .welcome)
        #expect(session.startError == APIError.offline.message)
    }
}


@Suite
@MainActor
struct ChatStoreTests {
    init() { StubProtocol.reset() }

    static let conversation = #"{"id":"c1","title":"Phương trình","created_at":1,"updated_at":2,"problem":"x+1=3","mode":"hint","hint_level":1,"solved":false,"is_geometry":false}"#
    static func message(_ id: String, role: String, text: String) -> String {
        #"{"id":"\#(id)","conversation_id":"c1","role":"\#(role)","text":"\#(text)","created_at":1,"image_url":null,"video_url":null,"has_drawing":false,"has_log":false,"channel":"chat","meta":{}}"#
    }
    static let events = """
        event: message
        data: \(message("m1", role: "user", text: "x+1=3"))

        event: progress
        data: {"stage":"tutor","label":"Gia sư đang suy nghĩ..."}

        event: delta
        data: {"text":"Em thử "}

        event: delta
        data: {"text":"chuyển vế nhé."}

        event: message
        data: \(message("m2", role: "assistant", text: "Em thử chuyển vế nhé."))

        event: conversation
        data: \(conversation.replacingOccurrences(of: #""hint_level":1"#, with: #""hint_level":2"#))

        event: done
        data: {}


        """

    private func store() -> ChatStore {
        StubProtocol.reply("/api/messages", json: #"{"conversation":\#(Self.conversation),"job_id":"j1"}"#)
        StubProtocol.reply("/api/conversations/c1", json: #"{"conversation":\#(Self.conversation.replacingOccurrences(of: #""hint_level":1"#, with: #""hint_level":2"#)),"messages":[\#(Self.message("m1", role: "user", text: "x+1=3")),\#(Self.message("m2", role: "assistant", text: "Em thử chuyển vế nhé."))]}"#)
        return ChatStore(api: client())
    }

    private func waitUntilIdle(_ chat: ChatStore) async {
        for _ in 0..<200 where chat.pending["c1"] != nil { try? await Task.sleep(for: .milliseconds(20)) }
    }

    @Test func aTurnStreamsThenSavesTheReply() async throws {
        StubProtocol.queue("/api/jobs/j1/events", events: Self.events)
        let chat = store()
        var finished = 0
        chat.onTurnFinished = { finished += 1 }
        let id = await chat.send(text: "x+1=3")
        #expect(id == "c1")
        #expect(chat.pending["c1"]?.text == "x+1=3")
        await waitUntilIdle(chat)
        #expect(chat.pending["c1"] == nil)
        let detail = try #require(chat.details["c1"])
        #expect(detail.messages.map(\.id) == ["m1", "m2"])
        #expect(detail.conversation.hintLevel == 2)
        #expect(finished == 1)
        let sent = try #require(StubProtocol.requests.first { $0.url?.path == "/api/messages" }?.httpBody)
        #expect(String(decoding: sent, as: UTF8.self).contains("name=\"text\"\r\n\r\nx+1=3"))
    }

    @Test func aDroppedStreamIsFollowedAgainWithoutDoublingTheReply() async throws {
        // The first connection drops after one piece; the server replays everything after.
        let dropped = Self.events.components(separatedBy: "event: delta")[0] + "event: delta\ndata: {\"text\":\"Em thử \"}\n\n"
        StubProtocol.queue("/api/jobs/j1/events", events: dropped)
        StubProtocol.queue("/api/jobs/j1/events", events: Self.events)
        let chat = store()
        await chat.send(text: "x+1=3")
        for _ in 0..<200 where chat.pending["c1"]?.label != "" && chat.pending["c1"] != nil {
            try? await Task.sleep(for: .milliseconds(20))
        }
        await waitUntilIdle(chat)
        #expect(StubProtocol.requests.filter { $0.url?.path == "/api/jobs/j1/events" }.count == 2)
        #expect(chat.details["c1"]?.messages.map(\.text) == ["x+1=3", "Em thử chuyển vế nhé."])
    }

    @Test func aRefusedMessageShowsTheServerReason() async {
        StubProtocol.reply("/api/messages", status: 429, json: #"{"detail":"Bạn đã dùng hết 10 lượt dùng AI hôm nay."}"#)
        let chat = ChatStore(api: client())
        let id = await chat.send(text: "x+1=3")
        #expect(id == nil)
        #expect(chat.notice?.text == "Bạn đã dùng hết 10 lượt dùng AI hôm nay.")
        #expect(chat.notice?.isError == true)
    }
}
}

struct MathBlocksTests {
    @Test func paragraphsDisplayFormulasAndInlineMath() {
        let blocks = MathBlocks.parse("Ta có $a^2$ và **b**.\n\n$$\nx = 1\n$$\n\n- Bước $1$\n## Kết luận")
        #expect(blocks == [
            .paragraph([.init(kind: .plain, pieces: [.text("Ta có "), .math("a^2"), .text(" và **b**.")])]),
            .display("x = 1"),
            .paragraph([.init(kind: .bullet, pieces: [.text("Bước "), .math("1")]),
                        .init(kind: .heading, pieces: [.text("Kết luận")])]),
        ])
    }

    @Test func unclosedFormulasAndMoneyStayText() {
        #expect(MathBlocks.pieces("Còn $x + 1") == [.text("Còn $x + 1")])
        #expect(MathBlocks.pieces("giá 5 $ và $ 3") == [.text("giá 5 $ và $ 3")])
        #expect(MathBlocks.parse("Đang viết $$x+") == [.paragraph([.init(kind: .plain, pieces: [.text("Đang viết $$x+")])])])
    }
}

struct SSEParserTests {
    @Test func eventsEndAtBlankLinesAndKeepAlivesAreIgnored() {
        var parser = SSEParser()
        let lines = [": keepalive", "", "event: delta", #"data: {"text":"Em "}"#, "",
                     "event: done", "data: {}", ""]
        let events = lines.compactMap { parser.feed($0) }
        #expect(events == [JobEvent(kind: "delta", data: #"{"text":"Em "}"#), JobEvent(kind: "done", data: "{}")])
    }

    @Test func multiLineDataIsJoined() {
        var parser = SSEParser()
        let events = ["event: message", "data: a", "data:b", ""].compactMap { parser.feed($0) }
        #expect(events == [JobEvent(kind: "message", data: "a\nb")])
    }
}
