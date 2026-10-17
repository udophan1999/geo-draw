import Foundation

// The JSON shapes of api/schemas.py and api/routers/*.py (web/src/lib/api.ts has the same).

struct User: Codable, Equatable, Sendable {
    enum Role: String, Codable, Sendable { case user, admin }
    let id: String
    let name: String
    let role: Role
}

struct Quota: Codable, Equatable, Sendable {
    let used: Int
    let limit: Int
}

/// GET /api/auth/me; login and register answer the same, plus `token` for the app.
struct Me: Codable, Equatable, Sendable {
    let user: User?
    let quota: Quota
    let aiAvailable: Bool
    var token: String?
}

enum TutorMode: String, Codable, Sendable { case hint, solution }

struct Conversation: Codable, Equatable, Identifiable, Sendable {
    let id: String
    var title: String
    let createdAt: Double
    let updatedAt: Double
    let problem: String
    let mode: TutorMode
    let hintLevel: Int
    /// The student reached the final answer (reported by the tutor in hint mode).
    let solved: Bool
    let isGeometry: Bool

    var updated: Date { Date(timeIntervalSince1970: updatedAt) }
}

struct Message: Codable, Equatable, Identifiable, Sendable {
    enum Role: String, Codable, Sendable { case user, assistant }
    /// `chat`: the tutor conversation; `figure`: drawing requests and drawings.
    enum Channel: String, Codable, Sendable { case chat, figure }
    struct Meta: Codable, Equatable, Sendable {
        var mode: TutorMode?
        var hintLevel: Int?
        var solved: Bool?
        var error: Bool?
    }

    let id: String
    let conversationId: String
    let role: Role
    let text: String
    let createdAt: Double
    let imageUrl: String?
    let videoUrl: String?
    let hasDrawing: Bool
    let hasLog: Bool
    let channel: Channel
    let meta: Meta
}

struct ConversationDetail: Codable, Equatable, Sendable {
    let conversation: Conversation
    let messages: [Message]
}

struct DrawSettings: Codable, Equatable, Sendable {
    enum Mode: String, Codable, CaseIterable, Sendable { case ai, parser }
    enum Model: String, Codable, CaseIterable, Sendable {
        case flash = "deepseek-v4-flash"
        case pro = "deepseek-v4-pro"
    }
    enum Quality: String, Codable, CaseIterable, Sendable { case l, m, h }

    var mode: Mode
    var model: Model
    var quality: Quality
    var animate: Bool
}

struct Example: Codable, Equatable, Hashable, Sendable {
    let topic: String
    let name: String
    let problem: String
}

/// GET /api/app-config: builds below `minIosBuild` must update.
struct AppConfig: Codable, Equatable, Sendable {
    let minIosBuild: Int
    let iosStoreUrl: String?
}

struct HelpText: Codable, Sendable {
    let markdown: String
}

/// The API's JSON uses snake_case.
extension JSONDecoder {
    static let api: JSONDecoder = {
        let decoder = JSONDecoder()
        decoder.keyDecodingStrategy = .convertFromSnakeCase
        return decoder
    }()
}

extension JSONEncoder {
    static let api: JSONEncoder = {
        let encoder = JSONEncoder()
        encoder.keyEncodingStrategy = .convertToSnakeCase
        return encoder
    }()
}
