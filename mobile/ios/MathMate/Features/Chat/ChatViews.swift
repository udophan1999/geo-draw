import SwiftUI

/// A new conversation: a greeting and example problems (web: the empty ChatPage). The composer
/// and sending come in phase 3.
struct NewConversationView: View {
    @Environment(SessionStore.self) private var session
    @State private var examples: [Example] = []

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(greeting).font(.largeTitle.bold())
                    Text("Gửi đề bài (gõ hoặc chụp ảnh), \(Brand.appName) sẽ gợi ý từng bước để em tự giải.")
                        .foregroundStyle(.secondary)
                }
                if !examples.isEmpty {
                    Text("Thử một bài mẫu").font(.headline)
                    LazyVGrid(columns: [GridItem(.adaptive(minimum: 260), spacing: 12)], spacing: 12) {
                        ForEach(examples, id: \.self) { example in
                            ExampleCard(example: example)
                        }
                    }
                }
            }
            .padding(16)
            .frame(maxWidth: 720, alignment: .leading)
            .frame(maxWidth: .infinity)
        }
        .navigationTitle("Cuộc trò chuyện mới")
        .navigationBarTitleDisplayMode(.inline)
        .task { examples = (try? await session.api.examples()) ?? [] }
    }

    private var greeting: String {
        if let name = session.user?.name { return "Chào \(name)!" }
        return "Chào bạn!"
    }
}

private struct ExampleCard: View {
    let example: Example

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(example.topic.uppercased()).font(.caption2.weight(.semibold)).foregroundStyle(Brand.primary)
            Text(example.name).font(.subheadline.weight(.semibold))
            Text(example.problem).font(.footnote).foregroundStyle(.secondary).lineLimit(3)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(Color(.secondarySystemBackground), in: .rect(cornerRadius: 14))
    }
}

/// An opened conversation. The messages, composer and figure arrive in phases 3–6.
struct ConversationView: View {
    @Environment(SessionStore.self) private var session
    let id: String
    @State private var detail: ConversationDetail?
    @State private var error: String?

    var body: some View {
        Group {
            if let detail {
                List(detail.messages.filter { $0.channel == .chat }) { message in
                    VStack(alignment: .leading, spacing: 4) {
                        Text(message.role == .user ? "Em" : Brand.appName)
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.secondary)
                        Text(message.text)
                    }
                }
                .navigationTitle(detail.conversation.title)
            } else if let error {
                ContentUnavailableView("Không mở được", systemImage: "exclamationmark.triangle", description: Text(error))
            } else {
                ProgressView()
            }
        }
        .navigationBarTitleDisplayMode(.inline)
        .task(id: id) { await load() }
    }

    private func load() async {
        detail = nil
        error = nil
        do {
            detail = try await session.api.conversation(id)
        } catch {
            self.error = error.localizedDescription
        }
    }
}
