import Foundation
import Observation

/// The conversation list (web: the Sidebar's query), kept in memory while the app runs.
@MainActor
@Observable
final class ConversationsStore {
    private(set) var items: [Conversation] = []
    private(set) var loaded = false
    var error: String?

    private let api: APIClient

    init(api: APIClient) { self.api = api }

    func load() async {
        do {
            items = try await api.conversations()
            error = nil
        } catch {
            self.error = error.localizedDescription
        }
        loaded = true
    }

    func rename(_ conversation: Conversation, to title: String) async {
        let title = title.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !title.isEmpty, title != conversation.title else { return }
        do {
            let renamed = try await api.rename(conversation.id, title: title)
            if let index = items.firstIndex(where: { $0.id == renamed.id }) { items[index] = renamed }
        } catch {
            self.error = error.localizedDescription
        }
    }

    func delete(_ conversation: Conversation) async {
        let before = items
        items.removeAll { $0.id == conversation.id }  // at once; put back if the server refuses
        do {
            try await api.deleteConversation(conversation.id)
        } catch {
            items = before
            self.error = error.localizedDescription
        }
    }

    /// Signing in or out shows someone else's list.
    func reset() {
        items = []
        loaded = false
        error = nil
    }
}
