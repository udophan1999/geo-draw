import Foundation

/// An error the user can read: the server's Vietnamese `detail`, or a connection problem.
struct APIError: LocalizedError, Equatable, Sendable {
    /// 0 when the server was not reached.
    let status: Int
    let message: String
    /// Free usernames offered when the chosen one is taken (409 on register).
    var suggestions: [String] = []

    var errorDescription: String? { message }

    static let offline = APIError(status: 0, message: "Không kết nối được máy chủ. Kiểm tra mạng rồi thử lại.")
    static let unexpected = APIError(status: 0, message: "Có lỗi xảy ra. Hãy thử lại.")
}

/// The FastAPI server in api/, as the app calls it: every request says `X-Client: ios`, carries
/// the session token as `Authorization: Bearer` and the guest id as `X-Guest-Id` (api/deps.py).
final class APIClient: Sendable {
    let baseURL: URL
    let session: URLSession
    private let credentials: CredentialStore

    init(baseURL: URL, credentials: CredentialStore, session: URLSession = .shared) {
        self.baseURL = baseURL
        self.credentials = credentials
        self.session = session
    }

    /// The URL in Info.plist (`MMAPIBaseURL`, set per build configuration in project.yml).
    static func configured(credentials: CredentialStore = KeychainCredentials()) -> APIClient {
        let value = Bundle.main.object(forInfoDictionaryKey: "MMAPIBaseURL") as? String
        let url = value.flatMap(URL.init(string:)) ?? URL(string: "http://127.0.0.1:8000")!
        return APIClient(baseURL: url, credentials: credentials)
    }

    var isSignedIn: Bool { credentials.token != nil }

    // MARK: Requests

    /// A request with the app's headers; `path` is relative to `/api/`.
    func request(_ path: String, method: String = "GET") -> URLRequest {
        var request = URLRequest(url: baseURL.appending(path: "api/\(path)"))
        request.httpMethod = method
        request.setValue("ios", forHTTPHeaderField: "X-Client")
        if let token = credentials.token {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        if let guestID = credentials.guestID {
            request.setValue(guestID, forHTTPHeaderField: "X-Guest-Id")
        }
        return request
    }

    /// Sends a request and checks the answer; returns the body.
    @discardableResult
    func send(_ request: URLRequest) async throws -> Data {
        let data: Data
        let response: URLResponse
        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.offline
        }
        guard let http = response as? HTTPURLResponse else { throw APIError.unexpected }
        // A new guest id comes back in a header the first time (api/main.py).
        if let guestID = http.value(forHTTPHeaderField: "X-Guest-Id") {
            credentials.guestID = guestID
        }
        guard (200..<300).contains(http.statusCode) else {
            throw Self.error(status: http.statusCode, body: data)
        }
        return data
    }

    func get<T: Decodable>(_ path: String, as type: T.Type = T.self) async throws -> T {
        try decode(try await send(request(path)))
    }

    func send<Body: Encodable, T: Decodable>(_ path: String, method: String, json body: Body,
                                            as type: T.Type = T.self) async throws -> T {
        try decode(try await send(jsonRequest(path, method: method, body: body)))
    }

    func send<Body: Encodable>(_ path: String, method: String, json body: Body) async throws {
        try await send(jsonRequest(path, method: method, body: body))
    }

    private func jsonRequest<Body: Encodable>(_ path: String, method: String, body: Body) throws -> URLRequest {
        var request = request(path, method: method)
        request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        request.httpBody = try JSONEncoder.api.encode(body)
        return request
    }

    private func decode<T: Decodable>(_ data: Data) throws -> T {
        do {
            return try JSONDecoder.api.decode(T.self, from: data)
        } catch {
            throw APIError.unexpected
        }
    }

    /// FastAPI errors: `{"detail": "…"}`, validation errors `{"detail": [{"msg": "…"}]}`, and
    /// register's `{"detail": "…", "suggestions": [...]}`.
    static func error(status: Int, body: Data) -> APIError {
        struct Detail: Decodable { let msg: String }
        struct Body: Decodable {
            let detail: String?
            let details: [Detail]?
            let suggestions: [String]?
            enum CodingKeys: String, CodingKey { case detail, suggestions }
            init(from decoder: Decoder) throws {
                let container = try decoder.container(keyedBy: CodingKeys.self)
                detail = try? container.decode(String.self, forKey: .detail)
                details = try? container.decode([Detail].self, forKey: .detail)
                suggestions = try? container.decode([String].self, forKey: .suggestions)
            }
        }
        let parsed = try? JSONDecoder().decode(Body.self, from: body)
        let message = parsed?.detail ?? parsed?.details?.first?.msg ?? APIError.unexpected.message
        return APIError(status: status, message: message, suggestions: parsed?.suggestions ?? [])
    }

    // MARK: Accounts

    func me() async throws -> Me { try await get("auth/me") }

    func login(username: String, password: String) async throws -> Me {
        try await signIn("auth/login", username: username, password: password)
    }

    func register(username: String, password: String) async throws -> Me {
        try await signIn("auth/register", username: username, password: password)
    }

    private func signIn(_ path: String, username: String, password: String) async throws -> Me {
        struct Credentials: Encodable { let username: String; let password: String }
        let me: Me = try await send(path, method: "POST", json: Credentials(username: username, password: password))
        credentials.token = me.token
        return me
    }

    /// Ends the session on the server too; the token is forgotten even when offline.
    func logout() async {
        defer { credentials.token = nil }
        _ = try? await send(request("auth/logout", method: "POST"))
    }

    func deleteAccount(password: String) async throws {
        struct Confirmation: Encodable { let password: String }
        try await send("auth/me", method: "DELETE", json: Confirmation(password: password))
        credentials.token = nil
    }

    // MARK: App data

    func appConfig() async throws -> AppConfig { try await get("app-config") }
    func settings() async throws -> DrawSettings { try await get("settings") }
    func saveSettings(_ settings: DrawSettings) async throws -> DrawSettings {
        try await send("settings", method: "PUT", json: settings)
    }
    func help() async throws -> String { try await get("help", as: HelpText.self).markdown }
    func examples() async throws -> [Example] { try await get("examples") }

    // MARK: Conversations

    func conversations() async throws -> [Conversation] { try await get("conversations") }
    func conversation(_ id: String) async throws -> ConversationDetail { try await get("conversations/\(id)") }

    func rename(_ id: String, title: String) async throws -> Conversation {
        struct Title: Encodable { let title: String }
        return try await send("conversations/\(id)", method: "PATCH", json: Title(title: title))
    }

    func deleteConversation(_ id: String) async throws {
        try await send(request("conversations/\(id)", method: "DELETE"))
    }
}
