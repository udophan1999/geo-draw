import PhotosUI
import SwiftUI

/// A conversation with the tutor, or a new one when `conversationId` is nil
/// (web: routes/ChatPage.tsx). The figure panel comes in phase 6; for now a sheet shows the
/// latest drawing.
struct ChatView: View {
    @Environment(SessionStore.self) private var session
    @Environment(ChatStore.self) private var chat
    let conversationId: String?
    /// A new conversation was created by the first message.
    let onCreated: (String) -> Void

    @State private var editing: Message?
    @State private var showingFigure = false

    private var detail: ConversationDetail? { conversationId.flatMap { chat.details[$0] } }
    private var turn: PendingTurn? { conversationId.flatMap { chat.pending[$0] } }
    private var chatMessages: [Message] { detail?.messages.filter { $0.channel == .chat } ?? [] }
    private var drawings: [Message] {
        detail?.messages.filter { $0.channel == .figure && $0.hasDrawing && $0.imageUrl != nil } ?? []
    }
    private var figureLabel: String? { conversationId.flatMap { chat.figures[$0] } }
    private var busy: Bool { turn != nil }
    /// Conversations from before the tutor have drawings only.
    private var legacyProblem: String? {
        guard let detail, chatMessages.isEmpty, turn == nil,
              detail.messages.contains(where: { $0.channel == .figure }) else { return nil }
        return detail.conversation.problem
    }

    var body: some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 18) {
                    if conversationId == nil || (detail != nil && chatMessages.isEmpty && turn == nil && legacyProblem == nil) {
                        WelcomeMessages { example in Task { await send(example.problem, image: nil) } }
                    }
                    if let legacyProblem { LegacyProblem(problem: legacyProblem) }
                    ForEach(chatMessages) { message in
                        MessageRow(message: message,
                                   editable: !busy && message.id == chatMessages.last(where: { $0.role == .user })?.id,
                                   onEdit: { editing = message })
                    }
                    if let turn { PendingRow(turn: turn) }
                    Color.clear.frame(height: 1).id("bottom")
                }
                .padding(.horizontal, 16)
                .padding(.vertical, 12)
                .frame(maxWidth: 760)
                .frame(maxWidth: .infinity)
            }
            .scrollDismissesKeyboard(.interactively)
            // A conversation opens at its latest message; a new one at the greeting.
            .defaultScrollAnchor(conversationId == nil ? .top : .bottom)
            .onChange(of: chatMessages.count) { scrollDown(proxy) }
            .onChange(of: turn?.reply.count) { scrollDown(proxy) }
            .onChange(of: turn?.label) { scrollDown(proxy) }
        }
        .overlay {
            if let id = conversationId, detail == nil {
                if let error = chat.loadErrors[id] {
                    ContentUnavailableView("Không mở được", systemImage: "exclamationmark.triangle", description: Text(error))
                } else {
                    ProgressView()
                }
            }
        }
        .safeAreaInset(edge: .bottom) {
            VStack(spacing: 8) {
                if let detail, !chatMessages.isEmpty || legacyProblem != nil {
                    TutorBar(conversation: detail.conversation, busy: busy) { action in
                        Task { await act(action) }
                    }
                }
                ChatComposer(placeholder: detail == nil ? "Nhập đề bài hoặc đính kèm ảnh đề…"
                                                        : "Trả lời câu hỏi của gia sư, hoặc hỏi thêm…",
                             busy: busy || chat.sending) { text, image in
                    await send(text, image: image)
                }
            }
            .padding(.horizontal, 12)
            .padding(.bottom, 8)
            .frame(maxWidth: 760)
            .frame(maxWidth: .infinity)
        }
        .overlay(alignment: .top) { NoticeBanner() }
        .navigationTitle(detail?.conversation.title ?? "Cuộc trò chuyện mới")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            if let detail, !drawings.isEmpty || figureLabel != nil || detail.conversation.isGeometry {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { showingFigure = true } label: {
                        if figureLabel != nil {
                            ProgressView()
                        } else {
                            Label("Hình vẽ", systemImage: "triangle")
                        }
                    }
                    .accessibilityIdentifier("showFigure")
                }
            }
        }
        .sheet(isPresented: $showingFigure) {
            if let id = conversationId {
                FigureSheet(conversationId: id, drawings: drawings, label: figureLabel)
                    .presentationDetents([.medium, .large])
            }
        }
        .sheet(item: $editing) { message in
            EditMessageSheet(message: message) { text in
                guard let id = conversationId else { return false }
                return await chat.edit(conversationId: id, messageId: message.id, text: text)
            }
        }
        .task(id: conversationId) {
            if let id = conversationId { await chat.load(id) }
        }
    }

    private func scrollDown(_ proxy: ScrollViewProxy) {
        withAnimation(.easeOut(duration: 0.2)) { proxy.scrollTo("bottom", anchor: .bottom) }
    }

    private func send(_ text: String, image: (data: Data, preview: UIImage)?) async -> Bool {
        guard let id = await chat.send(text: text, image: image, conversationId: conversationId) else { return false }
        Haptics.tap()
        if conversationId == nil { onCreated(id) }
        return true
    }

    private func act(_ action: TutorAction) async {
        guard let id = conversationId else { return }
        await chat.send(text: "", conversationId: id, action: action)
    }
}

// MARK: - Messages

private struct MessageRow: View {
    let message: Message
    let editable: Bool
    let onEdit: () -> Void

    var body: some View {
        if message.role == .user {
            HStack {
                Spacer(minLength: 48)
                UserBubble(text: message.text, image: message.imageUrl.map(Image.Source.remote))
                    .contextMenu {
                        if !message.text.isEmpty {
                            Button("Sao chép", systemImage: "doc.on.doc") { UIPasteboard.general.string = message.text }
                        }
                        if editable {
                            Button("Sửa tin nhắn", systemImage: "pencil", action: onEdit)
                        }
                    }
            }
            .accessibilityIdentifier("userMessage")
        } else {
            AssistantRow {
                VStack(alignment: .leading, spacing: 8) {
                    MathText(text: message.text)
                        .padding(message.meta.error == true ? 10 : 0)
                        .background(message.meta.error == true ? Color.red.opacity(0.1) : .clear, in: .rect(cornerRadius: 10))
                        .foregroundStyle(message.meta.error == true ? Color.red : .primary)
                    if message.meta.mode == .solution && message.meta.error != true {
                        Text("Lời giải chi tiết")
                            .font(.caption.weight(.medium))
                            .padding(.horizontal, 8).padding(.vertical, 3)
                            .background(Color(.secondarySystemFill), in: .capsule)
                    }
                }
                .contextMenu {
                    Button("Sao chép", systemImage: "doc.on.doc") { UIPasteboard.general.string = message.text }
                }
            }
            .accessibilityIdentifier("assistantMessage")
        }
    }
}

private extension Image {
    enum Source { case remote(String), local(UIImage) }
}

private struct UserBubble: View {
    let text: String
    let image: Image.Source?

    var body: some View {
        VStack(alignment: .trailing, spacing: 8) {
            switch image {
            case .remote(let path):
                AuthImage(path: path).frame(maxHeight: 220).clipShape(.rect(cornerRadius: 10))
            case .local(let preview):
                Image(uiImage: preview).resizable().scaledToFit().frame(maxHeight: 220).clipShape(.rect(cornerRadius: 10))
            case nil:
                EmptyView()
            }
            if !text.isEmpty {
                // Keep the student's line breaks (the web adds Markdown hard breaks too).
                MathText(text: text)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 10)
        .background(Brand.primary.opacity(0.12), in: .rect(cornerRadius: 18))
    }
}

private struct AssistantRow<Content: View>: View {
    @ViewBuilder var content: Content

    var body: some View {
        HStack(alignment: .top, spacing: 10) {
            Image("Logo")
                .resizable()
                .frame(width: 26, height: 26)
                .clipShape(.rect(cornerRadius: 7, style: .continuous))
                .accessibilityHidden(true)
            content
            Spacer(minLength: 0)
        }
    }
}

private struct PendingRow: View {
    let turn: PendingTurn

    var body: some View {
        if !turn.userSaved {
            HStack {
                Spacer(minLength: 48)
                UserBubble(text: turn.text, image: turn.image.map(Image.Source.local))
            }
        }
        if !turn.reply.isEmpty {
            AssistantRow { MathText(text: turn.reply, cursor: true) }
                .accessibilityIdentifier("streamingReply")
        } else if !turn.label.isEmpty {
            AssistantRow {
                HStack(spacing: 8) {
                    ProgressView()
                    Text(turn.label).font(.subheadline).foregroundStyle(.secondary)
                }
            }
        }
    }
}

private struct LegacyProblem: View {
    let problem: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text("Đề bài").font(.subheadline.weight(.semibold))
            MathText(text: problem).foregroundStyle(.secondary)
            Text("Cuộc trò chuyện này được tạo trước khi có gia sư. Nhắn một câu bất kỳ (ví dụ “em nên bắt đầu từ đâu?”) để được gợi ý giải.")
                .font(.footnote).foregroundStyle(.secondary)
        }
        .padding(14)
        .background(Color(.secondarySystemBackground), in: .rect(cornerRadius: 14))
    }
}

/// The greeting and example problems of an empty conversation.
private struct WelcomeMessages: View {
    @Environment(SessionStore.self) private var session
    let onExample: (Example) -> Void
    @State private var examples: [Example] = []

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 6) {
                Text(session.user.map { "Chào \($0.name)!" } ?? "Chào bạn!").font(.largeTitle.bold())
                Text("Gửi đề bài (gõ hoặc chụp ảnh), \(Brand.appName) sẽ gợi ý từng bước để em tự giải.")
                    .foregroundStyle(.secondary)
            }
            if !examples.isEmpty {
                Text("Thử một bài mẫu").font(.headline)
                LazyVGrid(columns: [GridItem(.adaptive(minimum: 260), spacing: 12)], spacing: 12) {
                    ForEach(examples, id: \.self) { example in
                        Button { onExample(example) } label: { ExampleCard(example: example) }
                            .buttonStyle(.plain)
                    }
                }
            }
        }
        .padding(.top, 12)
        .task { examples = (try? await session.api.examples()) ?? [] }
    }
}

private struct ExampleCard: View {
    let example: Example

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(example.topic.uppercased()).font(.caption2.weight(.semibold)).foregroundStyle(Brand.primary)
            Text(example.name).font(.subheadline.weight(.semibold))
            MathText(text: example.problem, style: .footnote).foregroundStyle(.secondary).lineLimit(3)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(Color(.secondarySystemBackground), in: .rect(cornerRadius: 14))
    }
}

/// Errors and notes over the chat for a few seconds (web: the toasts).
private struct NoticeBanner: View {
    @Environment(ChatStore.self) private var chat

    var body: some View {
        if let notice = chat.notice {
            Label(notice.text, systemImage: notice.isError ? "exclamationmark.triangle.fill" : "info.circle.fill")
                .font(.footnote)
                .foregroundStyle(notice.isError ? Color.red : .primary)
                .padding(.horizontal, 14)
                .padding(.vertical, 10)
                .mmGlass(in: .capsule)
                .padding(.horizontal, 16)
                .padding(.top, 6)
                .transition(.move(edge: .top).combined(with: .opacity))
                .accessibilityIdentifier("notice")
                .onTapGesture { chat.notice = nil }
                .task(id: notice.id) {
                    try? await Task.sleep(for: .seconds(5))
                    if chat.notice?.id == notice.id { withAnimation { chat.notice = nil } }
                }
        }
    }
}

// MARK: - Composer (plain text for now; formula chips come in phase 4)

private struct ChatComposer: View {
    let placeholder: String
    let busy: Bool
    let onSend: (String, (data: Data, preview: UIImage)?) async -> Bool

    @State private var text = ""
    @State private var photo: PhotosPickerItem?
    @State private var image: (data: Data, preview: UIImage)?
    @State private var submitting = false
    @FocusState private var focused: Bool

    private var canSend: Bool {
        !busy && !submitting && (!text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || image != nil)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if let image {
                ZStack(alignment: .topTrailing) {
                    Image(uiImage: image.preview).resizable().scaledToFill()
                        .frame(width: 72, height: 72).clipShape(.rect(cornerRadius: 10))
                    Button { self.image = nil; photo = nil } label: {
                        Image(systemName: "xmark.circle.fill").symbolRenderingMode(.palette)
                            .foregroundStyle(.white, .black.opacity(0.6))
                    }
                    .accessibilityLabel("Bỏ ảnh")
                    .offset(x: 6, y: -6)
                }
            }
            HStack(alignment: .bottom, spacing: 10) {
                PhotosPicker(selection: $photo, matching: .images) {
                    Image(systemName: "photo.on.rectangle").font(.title3)
                }
                .accessibilityLabel("Đính kèm ảnh đề")
                .padding(.bottom, 6)
                TextField(placeholder, text: $text, axis: .vertical)
                    .lineLimit(1...6)
                    .focused($focused)
                    .padding(.vertical, 8)
                    .accessibilityIdentifier("composer")
                Button {
                    Task { await submit() }
                } label: {
                    Group {
                        if submitting { ProgressView() } else { Image(systemName: "arrow.up.circle.fill").font(.title) }
                    }
                    .frame(width: 34, height: 34)
                }
                .disabled(!canSend)
                .accessibilityLabel("Gửi")
                .accessibilityIdentifier("send")
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 6)
        .mmGlass(in: .rect(cornerRadius: 24))
        .onChange(of: photo) {
            guard let photo else { return }
            Task {
                if let data = try? await photo.loadTransferable(type: Data.self) { image = ImagePrep.prepare(data) }
            }
        }
    }

    private func submit() async {
        guard canSend else { return }
        submitting = true
        defer { submitting = false }
        if await onSend(text.trimmingCharacters(in: .whitespacesAndNewlines), image) {
            text = ""
            image = nil
            photo = nil
        }
    }
}

// MARK: - Editing the last message

private struct EditMessageSheet: View {
    @Environment(\.dismiss) private var dismiss
    let message: Message
    let onSave: (String) async -> Bool
    @State private var text = ""
    @State private var saving = false
    @FocusState private var focused: Bool

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    TextField("Tin nhắn", text: $text, axis: .vertical)
                        .lineLimit(3...12)
                        .focused($focused)
                        .accessibilityIdentifier("editText")
                } footer: {
                    Text("\(Brand.appName) sẽ trả lời lại tin nhắn đã sửa (tốn 1 lượt AI).")
                }
            }
            .navigationTitle("Sửa tin nhắn")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Hủy") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Gửi lại") {
                        Task {
                            saving = true
                            if await onSave(text.trimmingCharacters(in: .whitespacesAndNewlines)) { dismiss() }
                            saving = false
                        }
                    }
                    .disabled(saving || text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || text == message.text)
                    .accessibilityIdentifier("saveEdit")
                }
            }
        }
        .onAppear {
            text = message.text
            focused = true  // straight to the keyboard
        }
        .presentationDetents([.medium, .large])
    }
}

// MARK: - The figure (the full panel comes in phase 6)

private struct FigureSheet: View {
    @Environment(ChatStore.self) private var chat
    let conversationId: String
    let drawings: [Message]
    let label: String?

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(spacing: 16) {
                    if let label {
                        HStack(spacing: 8) { ProgressView(); Text(label).foregroundStyle(.secondary) }
                            .padding(.top, 24)
                    }
                    if let path = drawings.last?.imageUrl {
                        AuthImage(path: path)
                            .background(Color.white, in: .rect(cornerRadius: 12))
                            .padding(.horizontal, 16)
                    } else if label == nil {
                        ContentUnavailableView("Chưa có hình vẽ", systemImage: "triangle",
                                               description: Text("Bấm “Vẽ hình” để \(Brand.appName) vẽ hình cho đề bài."))
                    }
                }
            }
            .navigationTitle("Hình vẽ")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .confirmationAction) {
                    Button(drawings.isEmpty ? "Vẽ hình" : "Vẽ lại") {
                        Task { await chat.drawFigure(conversationId: conversationId) }
                    }
                    .disabled(label != nil)
                }
            }
        }
    }
}
