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
