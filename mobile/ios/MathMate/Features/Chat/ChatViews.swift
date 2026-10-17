import SwiftUI

/// A conversation with the tutor, or a new one when `conversationId` is nil
/// (web: routes/ChatPage.tsx). The figure lives in an inspector: a sheet on iPhone, a column on
/// the right on iPad (shown by itself for geometry problems there).
struct ChatView: View {
    @Environment(SessionStore.self) private var session
    @Environment(ChatStore.self) private var chat
    let conversationId: String?
    /// A new conversation was created by the first message.
    let onCreated: (String) -> Void

    @State private var editing: Message?
    @State private var showingFigure = false
    @Environment(\.horizontalSizeClass) private var sizeClass

    private var detail: ConversationDetail? { conversationId.flatMap { chat.details[$0] } }
    private var turn: PendingTurn? { conversationId.flatMap { chat.pending[$0] } }
    private var chatMessages: [Message] { detail?.messages.filter { $0.channel == .chat } ?? [] }
    private var drawings: [Message] {
        detail?.messages.filter { $0.channel == .figure && $0.hasDrawing && $0.imageUrl != nil } ?? []
    }
    private var figureLabel: String? { conversationId.flatMap { chat.figures[$0] } }
    private var figureMessages: [Message] { detail?.messages.filter { $0.channel == .figure } ?? [] }
    /// Shown for geometry problems, or once a figure was asked for (web: hasFigurePanel).
    private var hasFigure: Bool {
        !figureMessages.isEmpty || figureLabel != nil || detail?.conversation.isGeometry == true
    }
    private var figureFailed: Bool {
        figureLabel == nil && figureMessages.last.map { $0.role == .assistant && !$0.hasDrawing } == true
    }
    /// The figure card goes after the last chat message sent before the newest figure message.
    private var figureCardAfter: String? {
        guard let newest = figureMessages.last else { return nil }
        return chatMessages.last(where: { $0.createdAt <= newest.createdAt })?.id
    }
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
                    if hasFigure && figureCardAfter == nil && !figureMessages.isEmpty { figureCard }
                    ForEach(chatMessages) { message in
                        MessageRow(message: message,
                                   editable: !busy && message.id == chatMessages.last(where: { $0.role == .user })?.id,
                                   onEdit: { editing = message })
                        if message.id == figureCardAfter { figureCard }
                    }
                    if figureMessages.isEmpty && figureLabel != nil { figureCard }
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
                ChatComposer(placeholder: detail == nil ? "Nhập đề bài hoặc chụp ảnh đề…"
                                                        : "Trả lời câu hỏi của gia sư, hoặc hỏi thêm…",
                             busy: busy || chat.sending,
                             onDraw: canAskForFigure ? { Task { await draw() } } : nil) { text, image in
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
            if detail != nil, hasFigure {
                ToolbarItem(placement: .topBarTrailing) {
                    Button { showingFigure.toggle() } label: {
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
        .inspector(isPresented: $showingFigure) {
            Group {
                if let id = conversationId {
                    DrawingPanel(conversationId: id)
                } else {
                    EmptyView()
                }
            }
            .inspectorColumnWidth(min: 320, ideal: 420, max: 560)
            .presentationDetents([.medium, .large])
        }
        // iPad: the figure column opens by itself for a geometry problem.
        .onChange(of: hasFigure, initial: true) {
            if sizeClass == .regular && hasFigure { showingFigure = true }
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

    private var figureCard: some View {
        FigureCard(latest: drawings.last, busyLabel: figureLabel, failed: figureFailed) { showingFigure = true }
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

    /// "Vẽ hình" in the composer when no figure is shown yet (geometry problems get the figure
    /// button in the toolbar, and their figure is drawn by itself).
    private var canAskForFigure: Bool {
        guard let detail else { return false }
        return !detail.conversation.isGeometry && drawings.isEmpty && figureLabel == nil
    }

    private func draw() async {
        guard let id = conversationId else { return }
        if await chat.drawFigure(conversationId: id) { showingFigure = true }
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
