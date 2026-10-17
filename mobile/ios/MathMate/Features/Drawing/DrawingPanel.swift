import AVKit
import SwiftUI

/// The figure of a conversation (web: drawing/DrawingPanel.tsx): the versions drawn so far,
/// progress while one is drawn, the failure with "Vẽ lại", the "Yêu cầu chỉnh hình" box, the
/// video and sharing.
struct DrawingPanel: View {
    @Environment(ChatStore.self) private var chat
    let conversationId: String

    @State private var picked: String?
    @State private var request = ""
    @State private var sending = false
    @FocusState private var refineFocused: Bool

    private var messages: [Message] {
        chat.details[conversationId]?.messages.filter { $0.channel == .figure } ?? []
    }
    private var drawings: [Message] { messages.filter { $0.hasDrawing && $0.imageUrl != nil } }
    private var requests: [String] { messages.filter { $0.role == .user && !$0.text.isEmpty }.map(\.text) }
    private var busyLabel: String? { chat.figures[conversationId] }
    /// The last drawing turn failed (an assistant figure message without a drawing).
    private var failure: Message? {
        guard busyLabel == nil, let last = messages.last, last.role == .assistant, !last.hasDrawing else { return nil }
        return last
    }
    /// A pick holds until a new drawing arrives, which is then shown (web: pickKey).
    private var shown: Message? {
        drawings.first { $0.id == picked } ?? drawings.last
    }

    var body: some View {
        ScrollViewReader { proxy in
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                if let shown {
                    header(shown).id("top")
                    status
                    if let path = shown.imageUrl { DrawingImage(path: path) }
                    refineBox
                    if let video = shown.videoUrl { DrawingVideo(path: video) }
                } else {
                    empty
                }
            }
            .padding(16)
            .padding(.top, 8)  // clear of the sheet's grabber
        }
        // A new version: show it from the top, with the version buttons.
        .onChange(of: drawings.count) {
            picked = nil
            withAnimation { proxy.scrollTo("top", anchor: .top) }
        }
        }
        .accessibilityIdentifier("drawingPanel")
    }

    private func header(_ shown: Message) -> some View {
        let index = drawings.firstIndex(of: shown) ?? 0
        return HStack(alignment: .center) {
            VStack(alignment: .leading, spacing: 2) {
                Text("Hình vẽ").font(.headline)
                Text(index == drawings.count - 1 ? "Phiên bản mới nhất" : "Phiên bản \(index + 1)/\(drawings.count)")
                    .font(.caption).foregroundStyle(.secondary)
                    .accessibilityIdentifier("drawingVersion")
            }
            Spacer()
            if drawings.count > 1 {
                HStack(spacing: 4) {
                    ForEach(Array(drawings.enumerated()), id: \.element.id) { offset, drawing in
                        Button("\(offset + 1)") { picked = drawing.id }
                            .buttonStyle(.plain)
                            .font(.footnote.weight(.semibold))
                            .frame(minWidth: 30, minHeight: 28)
                            .foregroundStyle(drawing.id == shown.id ? Color.white : .primary)
                            .background(drawing.id == shown.id ? Brand.primary : Color(.tertiarySystemFill), in: .rect(cornerRadius: 7))
                            .accessibilityLabel("Phiên bản \(offset + 1)")
                            .accessibilityIdentifier("version-\(offset + 1)")
                    }
                }
                .accessibilityElement(children: .contain)
                .accessibilityLabel("Phiên bản hình")
            }
            if let path = shown.imageUrl { ShareDrawing(path: path) }
        }
    }

    @ViewBuilder
    private var status: some View {
        if let busyLabel {
            HStack(spacing: 8) {
                ProgressView()
                Text(busyLabel).font(.subheadline).foregroundStyle(.secondary)
            }
            .accessibilityIdentifier("drawingProgress")
        } else if let failure {
            HStack(alignment: .top, spacing: 8) {
                Image(systemName: "exclamationmark.triangle.fill")
                Text(failure.text).frame(maxWidth: .infinity, alignment: .leading)
                Button("Vẽ lại") { Task { await chat.drawFigure(conversationId: conversationId) } }
                    .font(.footnote.weight(.semibold))
                    .accessibilityIdentifier("redraw")
            }
            .font(.subheadline)
            .foregroundStyle(.red)
            .padding(12)
            .background(Color.red.opacity(0.1), in: .rect(cornerRadius: 12))
            .accessibilityIdentifier("drawingFailure")
        }
    }

    private var empty: some View {
        VStack(spacing: 14) {
            if busyLabel != nil {
                ProgressView().controlSize(.large)
            } else {
                Image("Logo").resizable().frame(width: 56, height: 56)
                    .clipShape(.rect(cornerRadius: 13, style: .continuous))
                    .opacity(0.3).saturation(0)
            }
            Text(busyLabel ?? "Hình vẽ sẽ hiện ở đây").font(.subheadline).foregroundStyle(.secondary)
            if busyLabel == nil && failure == nil {
                Button("Vẽ hình") { Task { await chat.drawFigure(conversationId: conversationId) } }
                    .mmGlassButton()
                    .accessibilityIdentifier("drawNow")
            }
            if failure != nil { status }
        }
        .frame(maxWidth: .infinity, minHeight: 280)
    }

    private var refineBox: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 8) {
                TextField("Yêu cầu chỉnh hình, vd: vẽ thêm đường cao AH", text: $request)
                    .textFieldStyle(.roundedBorder)
                    .submitLabel(.send)
                    .onSubmit { Task { await refine() } }
                    .focused($refineFocused)
                    .accessibilityIdentifier("refineField")
                Button { Task { await refine() } } label: {
                    Group { if sending || busyLabel != nil { ProgressView() } else { Image(systemName: "paperplane.fill") } }
                        .frame(width: 34, height: 34)
                }
                .disabled(sending || busyLabel != nil || request.trimmingCharacters(in: .whitespaces).isEmpty)
                .accessibilityLabel("Gửi yêu cầu chỉnh hình")
                .accessibilityIdentifier("sendRefine")
            }
            if !requests.isEmpty {
                Text("Đã yêu cầu: " + requests.map { "“\($0)”" }.joined(separator: " · "))
                    .font(.caption).foregroundStyle(.secondary)
            }
        }
    }

    private func refine() async {
        let text = request.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !sending, busyLabel == nil else { return }
        sending = true
        if await chat.drawFigure(conversationId: conversationId, text: text) {
            request = ""
            refineFocused = false  // the keyboard goes: the new version is drawn above
        }
        sending = false
    }
}

/// A drawing loaded with the session (images are private to their owner).
private struct DrawingImage: View {
    @Environment(SessionStore.self) private var session
    let path: String
    @State private var image: UIImage?

    var body: some View {
        Group {
            if let image {
                ZoomableImage(image: image)
            } else {
                ProgressView().frame(maxWidth: .infinity)
            }
        }
        .frame(height: 380)
        .task(id: path) { image = await ImageStore.image(at: path, api: session.api) }
    }
}

/// Shares the drawing (save to Photos, send in a message…).
private struct ShareDrawing: View {
    @Environment(SessionStore.self) private var session
    let path: String
    @State private var image: UIImage?

    var body: some View {
        // A fixed frame, so the task runs before there is a link to show (a task on an empty
        // view never starts).
        Color.clear
            .frame(width: 34, height: 30)
            .overlay {
                if let image {
                    ShareLink(item: Image(uiImage: image), preview: SharePreview("Hình vẽ", image: Image(uiImage: image))) {
                        Image(systemName: "square.and.arrow.up").frame(width: 34, height: 30)
                    }
                    .accessibilityLabel("Chia sẻ hình")
                    .accessibilityIdentifier("shareDrawing")
                }
            }
            .task(id: path) { image = await ImageStore.image(at: path, api: session.api) }
    }
}

/// The animated drawing. The file needs the session, so it is downloaded and played locally.
private struct DrawingVideo: View {
    @Environment(SessionStore.self) private var session
    let path: String
    @State private var player: AVPlayer?
    @State private var failed = false

    var body: some View {
        Group {
            if let player {
                VideoPlayer(player: player)
            } else if failed {
                Label("Không tải được video", systemImage: "video.slash").font(.footnote).foregroundStyle(.secondary)
            } else {
                ProgressView()
            }
        }
        .frame(height: 240)
        .frame(maxWidth: .infinity)
        .background(Color.black, in: .rect(cornerRadius: 14))
        .clipShape(.rect(cornerRadius: 14))
        .task(id: path) {
            guard let data = try? await session.api.file(at: path) else { failed = true; return }
            let url = FileManager.default.temporaryDirectory.appending(path: "mathmate-\(abs(path.hashValue)).mp4")
            do {
                try data.write(to: url, options: .atomic)
                player = AVPlayer(url: url)
            } catch {
                failed = true
            }
        }
    }
}

/// The figure in the chat: a thumbnail of the latest drawing, or the progress of the one being
/// drawn. A tap opens the drawing panel.
struct FigureCard: View {
    @Environment(SessionStore.self) private var session
    let latest: Message?
    let busyLabel: String?
    let failed: Bool
    let onOpen: () -> Void
    @State private var thumbnail: UIImage?

    var body: some View {
        Button(action: onOpen) {
            HStack(spacing: 12) {
                ZStack {
                    RoundedRectangle(cornerRadius: 10).fill(Color.white)
                    if let thumbnail {
                        Image(uiImage: thumbnail).resizable().scaledToFit().padding(4)
                    } else if busyLabel != nil {
                        ProgressView()
                    } else {
                        Image(systemName: failed ? "exclamationmark.triangle" : "triangle").foregroundStyle(.secondary)
                    }
                }
                .frame(width: 64, height: 64)
                .overlay(RoundedRectangle(cornerRadius: 10).stroke(.separator, lineWidth: 0.5))
                VStack(alignment: .leading, spacing: 3) {
                    Text("Hình vẽ").font(.subheadline.weight(.semibold))
                    Text(busyLabel ?? (failed ? "Chưa vẽ được hình" : "Chạm để xem, phóng to, chỉnh hình"))
                        .font(.caption).foregroundStyle(failed ? Color.red : .secondary)
                        .lineLimit(2)
                }
                Spacer()
                Image(systemName: "chevron.right").foregroundStyle(.tertiary)
            }
            .padding(10)
            .background(Color(.secondarySystemBackground), in: .rect(cornerRadius: 14))
        }
        .buttonStyle(.plain)
        .accessibilityIdentifier("figureCard")
        .task(id: latest?.imageUrl) {
            if let path = latest?.imageUrl { thumbnail = await ImageStore.image(at: path, api: session.api) }
        }
    }
}
