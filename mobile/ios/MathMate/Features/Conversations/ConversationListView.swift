import SwiftUI

/// The list of conversations with "new", rename and delete (web: components/Sidebar.tsx).
struct ConversationListView: View {
    @Environment(SessionStore.self) private var session
    @Environment(ConversationsStore.self) private var conversations
    @Binding var selection: String?
    let onNew: () -> Void
    let onSettings: () -> Void

    @State private var renaming: Conversation?
    @State private var newTitle = ""
    @State private var deleting: Conversation?

    var body: some View {
        List(selection: $selection) {
            if session.isGuest {
                Section {
                    GuestNotice()
                }
            }
            Section {
                ForEach(conversations.items) { conversation in
                    NavigationLink(value: conversation.id) {
                        ConversationRow(conversation: conversation)
                    }
                    .swipeActions(edge: .trailing) {
                        Button("Xóa", systemImage: "trash", role: .destructive) { deleting = conversation }
                        Button("Đổi tên", systemImage: "pencil") { startRenaming(conversation) }
                            .tint(.orange)
                    }
                    .contextMenu {
                        Button("Đổi tên", systemImage: "pencil") { startRenaming(conversation) }
                        Button("Xóa", systemImage: "trash", role: .destructive) { deleting = conversation }
                    }
                }
            } header: {
                if !conversations.items.isEmpty { Text("Cuộc trò chuyện") }
            }
        }
        .overlay {
            if conversations.loaded && conversations.items.isEmpty {
                ContentUnavailableView("Chưa có cuộc trò chuyện", systemImage: "bubble.left.and.text.bubble.right",
                                       description: Text("Gửi đề bài đầu tiên để bắt đầu."))
            } else if !conversations.loaded {
                ProgressView()
            }
        }
        .refreshable { await conversations.load() }
        .navigationTitle(Brand.appName)
        .toolbar {
            ToolbarItem(placement: .topBarLeading) {
                AccountMenu(onSettings: onSettings)
            }
            ToolbarItem(placement: .topBarTrailing) {
                Button("Cuộc trò chuyện mới", systemImage: "square.and.pencil", action: onNew)
                    .accessibilityIdentifier("newConversation")
            }
        }
        .alert("Đổi tên cuộc trò chuyện", isPresented: .init(get: { renaming != nil }, set: { if !$0 { renaming = nil } })) {
            TextField("Tên mới", text: $newTitle)
            Button("Hủy", role: .cancel) {}
            Button("Lưu") {
                if let conversation = renaming {
                    Task { await conversations.rename(conversation, to: newTitle) }
                }
            }
        }
        .confirmationDialog("Xóa cuộc trò chuyện?", isPresented: .init(get: { deleting != nil }, set: { if !$0 { deleting = nil } }),
                            titleVisibility: .visible, presenting: deleting) { conversation in
            Button("Xóa", role: .destructive) {
                if selection == conversation.id { selection = nil }
                Task { await conversations.delete(conversation) }
            }
        } message: { conversation in
            Text("«\(conversation.title)» và các hình vẽ trong đó sẽ bị xóa vĩnh viễn.")
        }
        .alert("Có lỗi", isPresented: .init(get: { conversations.error != nil && conversations.loaded },
                                            set: { if !$0 { conversations.error = nil } })) {
            Button("OK", role: .cancel) {}
        } message: {
            Text(conversations.error ?? "")
        }
    }

    private func startRenaming(_ conversation: Conversation) {
        newTitle = conversation.title
        renaming = conversation
    }
}

private struct ConversationRow: View {
    let conversation: Conversation

    var body: some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(conversation.title).lineLimit(1)
            HStack(spacing: 6) {
                if conversation.solved {
                    Label("Đã giải xong", systemImage: "checkmark.seal.fill").foregroundStyle(.green)
                } else if conversation.mode == .solution {
                    Label("Lời giải", systemImage: "list.number")
                } else {
                    Label("Gợi ý bậc \(conversation.hintLevel)", systemImage: "lightbulb")
                }
                Spacer()
                Text(conversation.updated, format: .relative(presentation: .named))
            }
            .font(.caption)
            .foregroundStyle(.secondary)
            .labelStyle(.titleAndIcon)
        }
        .padding(.vertical, 2)
    }
}

private struct GuestNotice: View {
    @Environment(SessionStore.self) private var session

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Đăng nhập để lưu lại lịch sử hỏi đáp").font(.subheadline)
            Button("Đăng nhập") { session.showWelcome() }
                .mmGlassButton(prominent: true)
                .controlSize(.small)
        }
        .padding(.vertical, 4)
    }
}

/// The account at the top of the list: settings, sign out (web: AccountBox).
private struct AccountMenu: View {
    @Environment(SessionStore.self) private var session
    let onSettings: () -> Void

    var body: some View {
        Menu {
            if let user = session.user {
                Section(user.name) {
                    Button("Cài đặt", systemImage: "gearshape", action: onSettings)
                    Button("Đăng xuất", systemImage: "rectangle.portrait.and.arrow.right", role: .destructive) {
                        Task { await session.logout() }
                    }
                }
            } else {
                Button("Cài đặt", systemImage: "gearshape", action: onSettings)
                Button("Đăng nhập", systemImage: "person.crop.circle") { session.showWelcome() }
            }
        } label: {
            if let user = session.user {
                Text(String(user.name.prefix(1)).uppercased())
                    .font(.subheadline.bold())
                    .foregroundStyle(.white)
                    .frame(width: 30, height: 30)
                    .background(Brand.primary, in: .circle)
            } else {
                Image(systemName: "person.crop.circle")
            }
        }
        .accessibilityLabel("Tài khoản")
        .accessibilityIdentifier("accountMenu")
    }
}
