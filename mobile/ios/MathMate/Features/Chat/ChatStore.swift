import Foundation
import Observation
import UIKit

/// A tutor turn in progress: the student's bubble at once, then the reply as it streams.
struct PendingTurn: Equatable {
    var text: String
    var image: UIImage?
    var label: String
    /// The server has stored the student's message (it is in the list now).
    var userSaved: Bool
    var reply: String
}

/// A short message over the chat (web: the toasts).
struct ChatNotice: Equatable, Identifiable {
    let id = UUID()
    let text: String
    var isError = false
}

/// The open conversations and their running jobs (web: lib/chat.tsx ChatProvider). Jobs run on
/// the server and save their results themselves; the app only follows their events, and
/// follows them again after a dropped connection (the server replays every event).
@MainActor
@Observable
final class ChatStore {
    private(set) var details: [String: ConversationDetail] = [:]
    private(set) var pending: [String: PendingTurn] = [:]
    /// Conversation id → progress label of the drawing being made.
    private(set) var figures: [String: String] = [:]
    private(set) var loadErrors: [String: String] = [:]
    private(set) var sending = false
    var notice: ChatNotice?

    /// Called when a turn changed the conversation list or the quota.
    var onTurnFinished: (() async -> Void)?

    private let api: APIClient
    private var jobs: [String: Task<Void, Never>] = [:]

    init(api: APIClient) { self.api = api }

    // MARK: Conversations

    func load(_ id: String) async {
        do {
            details[id] = try await api.conversation(id)
            loadErrors[id] = nil
        } catch {
            if details[id] == nil { loadErrors[id] = error.localizedDescription }
        }
    }

    /// Signing in or out shows someone else's conversations.
    func reset() {
        jobs.values.forEach { $0.cancel() }
        jobs = [:]
        details = [:]
        pending = [:]
        figures = [:]
        loadErrors = [:]
    }

    // MARK: Turns

    /// Sends a message or a button's action. Returns the conversation id once the server
    /// accepted it (a new conversation for the first message), nil after an error.
    @discardableResult
    func send(text: String, image: (data: Data, preview: UIImage)? = nil, conversationId: String? = nil,
              action: TutorAction = .ask) async -> String? {
        sending = true
        defer { sending = false }
        let started: StartedTurn
        do {
            started = try await api.sendMessage(text: text, conversationId: conversationId,
                                                image: image?.data, action: action)
        } catch {
            notice = ChatNotice(text: error.localizedDescription, isError: true)
            return nil
        }
        let id = started.conversation.id
        if details[id] == nil { details[id] = ConversationDetail(conversation: started.conversation, messages: []) }
        pending[id] = PendingTurn(text: text, image: image?.preview, label: "Đang gửi...", userSaved: false, reply: "")
        follow(started.jobId, conversation: id, figure: false)
        return id
    }

    /// Edits the student's last message; the tutor's reply to it is written again.
    func edit(conversationId: String, messageId: String, text: String) async -> Bool {
        let started: StartedTurn
        do {
            started = try await api.editMessage(messageId, text: text)
        } catch {
            notice = ChatNotice(text: error.localizedDescription, isError: true)
            return false
        }
        // Show the edited text and drop the old reply at once; the job sends the saved versions.
        if var detail = details[conversationId], let index = detail.messages.firstIndex(where: { $0.id == messageId }) {
            var messages = detail.messages.enumerated()
                .filter { $0.offset <= index || $0.element.channel != .chat }
                .map(\.element)
            messages[index] = messages[index].with(text: text)
            detail = ConversationDetail(conversation: detail.conversation, messages: messages)
            details[conversationId] = detail
        }
        pending[conversationId] = PendingTurn(text: text, image: nil, label: "Đang gửi...", userSaved: true, reply: "")
        follow(started.jobId, conversation: conversationId, figure: false)
        return true
    }

    /// Draws the figure (empty text) or refines it.
    func drawFigure(conversationId: String, text: String = "") async -> Bool {
        do {
            let job = try await api.drawFigure(conversationId, text: text)
            follow(job, conversation: conversationId, figure: true)
            return true
        } catch {
            notice = ChatNotice(text: error.localizedDescription, isError: true)
            return false
        }
    }

    func isBusy(_ conversationId: String) -> Bool { pending[conversationId] != nil }

    // MARK: Following jobs

    private func follow(_ jobId: String, conversation id: String, figure: Bool) {
        if figure { figures[id] = "Đang vẽ hình..." }
        jobs[jobId] = Task { [weak self] in
            await self?.run(jobId, conversation: id, figure: figure)
        }
    }

    private func run(_ jobId: String, conversation id: String, figure: Bool) async {
        var attempts = 0
        var finished = false
        while !finished && !Task.isCancelled {
            if !figure, pending[id] != nil { pending[id]?.reply = "" }  // the events start over
            do {
                for try await event in api.events(ofJob: jobId) {
                    if handle(event, conversation: id, figure: figure) { finished = true }
                }
            } catch let error as APIError where (400..<500).contains(error.status) {
                finished = true  // the job is gone (an hour after it ended): reload instead
            } catch {}
            if finished || Task.isCancelled { break }
            // Dropped (the app went to the background, the network changed): follow again.
            attempts += 1
            if attempts > 30 { break }
            try? await Task.sleep(for: .seconds(min(Double(attempts), 5)))
        }
        jobs[jobId] = nil
        guard !Task.isCancelled else { return }
        if figure { figures[id] = nil } else { pending[id] = nil }
        await load(id)
        await onTurnFinished?()
    }

    /// Applies one event; true when the job has ended.
    private func handle(_ event: JobEvent, conversation id: String, figure: Bool) -> Bool {
        let data = Data(event.data.utf8)
        switch event.kind {
        case "message":
            guard let message = try? JSONDecoder.api.decode(Message.self, from: data) else { break }
            upsert(message)
            if !figure {
                if message.role == .user { pending[id]?.userSaved = true }
                else { pending[id]?.reply = ""; pending[id]?.label = "" }  // the saved reply replaces the stream
            }
        case "delta":
            if let piece = try? JSONDecoder.api.decode(Piece.self, from: data) { pending[id]?.reply += piece.text }
        case "progress":
            if let progress = try? JSONDecoder.api.decode(Progress.self, from: data) {
                if figure { figures[id] = progress.label } else { pending[id]?.label = progress.label }
            }
        case "conversation":
            if let conversation = try? JSONDecoder.api.decode(Conversation.self, from: data), let detail = details[id] {
                details[id] = ConversationDetail(conversation: conversation, messages: detail.messages)
            }
        case "figure_job":
            if let job = try? JSONDecoder.api.decode(FigureJob.self, from: data), jobs[job.jobId] == nil {
                follow(job.jobId, conversation: id, figure: true)
            }
        case "figure_skipped":
            if let skipped = try? JSONDecoder.api.decode(Detail.self, from: data) {
                notice = ChatNotice(text: "Chưa vẽ hình: \(skipped.detail)")
            }
        case "failed":
            let detail = (try? JSONDecoder.api.decode(Detail.self, from: data))?.detail
            notice = ChatNotice(text: detail ?? APIError.unexpected.message, isError: true)
            return true
        case "done":
            if figure { Haptics.success() }
            return true
        default:
            break
        }
        return false
    }

    private func upsert(_ message: Message) {
        guard let detail = details[message.conversationId] else { return }
        var messages = detail.messages
        if let index = messages.firstIndex(where: { $0.id == message.id }) {
            messages[index] = message
        } else {
            messages.append(message)
        }
        details[message.conversationId] = ConversationDetail(conversation: detail.conversation, messages: messages)
    }

    private struct Piece: Decodable { let text: String }
    private struct Progress: Decodable { let label: String }
    private struct FigureJob: Decodable { let jobId: String }
    private struct Detail: Decodable { let detail: String }
}

extension Message {
    /// The same message with other text (an edit shown before the server confirms it).
    func with(text: String) -> Message {
        Message(id: id, conversationId: conversationId, role: role, text: text, createdAt: createdAt,
                imageUrl: imageUrl, videoUrl: videoUrl, hasDrawing: hasDrawing, hasLog: hasLog,
                channel: channel, meta: meta)
    }
}
