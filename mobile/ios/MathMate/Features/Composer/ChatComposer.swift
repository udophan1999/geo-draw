import PhotosUI
import SwiftUI

/// A formula being written: new (`range` nil) or a chip being edited.
private struct FormulaEdit: Identifiable {
    let id = UUID()
    let latex: String
    let range: NSRange?
}

/// The message box with its tools (web: chat/Composer.tsx): formula chips, the symbol bar,
/// the formula editor, a photo of the problem (camera, library, paste, drag and drop) and
/// "Vẽ hình" when the conversation has no figure yet.
struct ChatComposer: View {
    let placeholder: String
    let busy: Bool
    /// Shown when the conversation has no figure panel yet (web: the Composer's actions slot).
    var onDraw: (() -> Void)?
    let onSend: (String, (data: Data, preview: UIImage)?) async -> Bool

    @State private var controller = ComposerController()
    @State private var image: (data: Data, preview: UIImage)?
    @State private var photo: PhotosPickerItem?
    @State private var showingLibrary = false
    @State private var showingScanner = false
    @State private var showingSymbols = false
    @State private var formula: FormulaEdit?
    @State private var submitting = false

    private var canSend: Bool {
        !busy && !submitting && (!controller.text.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty || image != nil)
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            if let image { attachment(image.preview) }
            if showingSymbols { SymbolBar { controller.insert($0) } }
            ComposerField(controller: controller, placeholder: placeholder,
                          onSubmit: { Task { await submit() } },
                          onImage: { data in image = ImagePrep.prepare(data) },
                          onOpenFormula: { latex, range in formula = FormulaEdit(latex: latex, range: range) })
            toolRow
        }
        .padding(.horizontal, 14)
        .padding(.top, 6)
        .padding(.bottom, 8)
        .mmGlass(in: .rect(cornerRadius: 24))
        .dropDestination(for: Data.self) { items, _ in
            guard let data = items.first, let prepared = ImagePrep.prepare(data) else { return false }
            image = prepared
            return true
        }
        .photosPicker(isPresented: $showingLibrary, selection: $photo, matching: .images)
        .onChange(of: photo) {
            guard let photo else { return }
            Task {
                if let data = try? await photo.loadTransferable(type: Data.self) { image = ImagePrep.prepare(data) }
                self.photo = nil
            }
        }
        .fullScreenCover(isPresented: $showingScanner) {
            DocumentScanner { scanned in
                if let data = scanned.jpegData(compressionQuality: 0.9) { image = ImagePrep.prepare(data) }
            }
            .ignoresSafeArea()
        }
        .sheet(item: $formula) { edit in
            FormulaSheet(initialLatex: edit.latex, editingExisting: edit.range != nil) { latex in
                if let range = edit.range {
                    controller.replaceFormula(at: range, with: latex)
                } else {
                    controller.insertFormula(latex)
                }
            }
        }
    }

    private var toolRow: some View {
        HStack(spacing: 4) {
            Menu {
                if DocumentScanner.isAvailable {
                    Button("Chụp đề", systemImage: "doc.viewfinder") { showingScanner = true }
                }
                Button("Thư viện ảnh", systemImage: "photo.on.rectangle") { showingLibrary = true }
            } label: {
                tool("photo.badge.plus")
            }
            .accessibilityLabel("Đính kèm ảnh đề")
            .accessibilityIdentifier("attach")
            Button { withAnimation(.snappy) { showingSymbols.toggle() } } label: {
                // Ω, as on the web's button.
                Text("Ω")
                    .font(.title3.weight(.medium))
                    .frame(width: 34, height: 34)
                    .foregroundStyle(showingSymbols ? Color.white : Brand.primary)
                    .background(showingSymbols ? Brand.primary : .clear, in: .circle)
            }
            .accessibilityLabel("Ký hiệu toán")
            .accessibilityIdentifier("toggleSymbols")
            Button { formula = FormulaEdit(latex: "", range: nil) } label: { tool("sum") }
                .accessibilityLabel("Nhập công thức")
                .accessibilityIdentifier("openFormula")
            Spacer()
            if let onDraw {
                Button(action: onDraw) {
                    Label("Vẽ hình", systemImage: "triangle").font(.footnote.weight(.medium))
                }
                .buttonStyle(.borderless)
                .accessibilityIdentifier("drawFigure")
            }
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

    private func tool(_ systemImage: String) -> some View {
        Image(systemName: systemImage)
            .font(.body)
            .frame(width: 34, height: 34)
            .foregroundStyle(Brand.primary)
    }

    private func attachment(_ preview: UIImage) -> some View {
        ZStack(alignment: .topTrailing) {
            Image(uiImage: preview).resizable().scaledToFill()
                .frame(width: 72, height: 72).clipShape(.rect(cornerRadius: 10))
            Button { image = nil } label: {
                Image(systemName: "xmark.circle.fill").symbolRenderingMode(.palette)
                    .foregroundStyle(.white, .black.opacity(0.6))
            }
            .accessibilityLabel("Bỏ ảnh")
            .offset(x: 6, y: -6)
        }
        .padding(.top, 6)
        .accessibilityIdentifier("attachedImage")
    }

    private func submit() async {
        guard canSend else { return }
        submitting = true
        defer { submitting = false }
        if await onSend(controller.text.trimmingCharacters(in: .whitespacesAndNewlines), image) {
            controller.clear()
            image = nil
        }
    }
}

/// Editing the student's last message in the same box, chips and all (web: MessageList's
/// EditBubble).
struct EditMessageSheet: View {
    @Environment(\.dismiss) private var dismiss
    let message: Message
    let onSave: (String) async -> Bool
    @State private var controller = ComposerController()
    @State private var saving = false
    @State private var formula: FormulaEdit?

    private var text: String { controller.text.trimmingCharacters(in: .whitespacesAndNewlines) }

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: 12) {
                ComposerField(controller: controller, placeholder: "Tin nhắn", initialText: message.text,
                              autofocus: true, maxHeight: 260, identifier: "editText",
                              onSubmit: { Task { await save() } },
                              onOpenFormula: { latex, range in formula = FormulaEdit(latex: latex, range: range) })
                    .padding(12)
                    .background(Color(.secondarySystemBackground), in: .rect(cornerRadius: 14))
                Text("\(Brand.appName) sẽ trả lời lại tin nhắn đã sửa (tốn 1 lượt AI).")
                    .font(.footnote).foregroundStyle(.secondary)
                Spacer()
            }
            .padding(16)
            .navigationTitle("Sửa tin nhắn")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Hủy") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Gửi lại") { Task { await save() } }
                        .disabled(saving || text.isEmpty || text == message.text)
                        .accessibilityIdentifier("saveEdit")
                }
            }
            .sheet(item: $formula) { edit in
                FormulaSheet(initialLatex: edit.latex, editingExisting: edit.range != nil) { latex in
                    if let range = edit.range { controller.replaceFormula(at: range, with: latex) }
                }
            }
        }
        .presentationDetents([.medium, .large])
    }

    private func save() async {
        guard !saving, !text.isEmpty, text != message.text else { return }
        saving = true
        if await onSave(text) { dismiss() }
        saving = false
    }
}
