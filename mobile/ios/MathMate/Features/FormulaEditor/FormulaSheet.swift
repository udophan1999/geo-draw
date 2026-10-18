import SwiftUI

/// Writing a formula (web: chat/MathInput.tsx FormulaDialog with MathLive): visual by default,
/// with the math keyboard and the gallery; "Sửa LaTeX" for what the visual editor cannot open
/// (tables such as `cases`) or for typing LaTeX directly.
struct FormulaSheet: View {
    @Environment(\.dismiss) private var dismiss
    let initialLatex: String
    /// A template inserted at once, the caret in its first slot (the roots of the symbol bar).
    var initialTemplate: String? = nil
    let editingExisting: Bool
    let onDone: (String) -> Void

    @State private var model: FormulaEditorModel?
    @State private var latex = ""
    @State private var rawMode = false
    @State private var loaded = false

    private var current: String {
        (rawMode ? latex : model?.latex ?? latex).trimmingCharacters(in: .whitespacesAndNewlines)
    }

    var body: some View {
        NavigationStack {
            Group {
                if rawMode || model == nil {
                    RawLatexEditor(latex: $latex)
                } else if let model {
                    VStack(spacing: 0) {
                        GeometryReader { geometry in
                            ScrollView(.horizontal, showsIndicators: false) {
                                FormulaCanvasView(model: model, minWidth: geometry.size.width,
                                                  height: geometry.size.height)
                            }
                            .defaultScrollAnchor(.trailing)
                        }
                        .frame(minHeight: 150, maxHeight: .infinity)
                        .background(Color(.secondarySystemBackground), in: .rect(cornerRadius: 16))
                        .padding(16)
                        MathKeyboard(model: model)
                    }
                }
            }
            .navigationTitle(editingExisting ? "Sửa công thức" : "Công thức")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Hủy") { dismiss() } }
                ToolbarItem(placement: .principal) {
                    Button(rawMode ? "Bảng phím" : "Sửa LaTeX") { toggleMode() }
                        .font(.footnote)
                        .disabled(rawMode && FormulaEditorModel(latex: latex) == nil)
                        .accessibilityIdentifier("toggleLatex")
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button(editingExisting ? "Lưu" : "Chèn") {
                        onDone(current)
                        dismiss()
                    }
                    .disabled(current.isEmpty)
                    .accessibilityIdentifier("insertFormula")
                }
            }
        }
        .presentationDetents([.large])
        .onAppear {
            guard !loaded else { return }
            loaded = true
            latex = initialLatex
            model = FormulaEditorModel(latex: initialLatex)
            if let initialTemplate { model?.template(initialTemplate) }
            rawMode = model == nil  // a table (cases…) opens as LaTeX
        }
    }

    private func toggleMode() {
        if rawMode {
            if let fresh = FormulaEditorModel(latex: latex) { model = fresh; rawMode = false }
        } else {
            latex = model?.latex ?? latex
            rawMode = true
        }
    }
}

/// LaTeX with a live preview, and the gallery adding templates to it.
private struct RawLatexEditor: View {
    @Binding var latex: String
    @FocusState private var focused: Bool

    var body: some View {
        VStack(spacing: 0) {
            preview
                .frame(maxWidth: .infinity, minHeight: 90)
                .background(Color(.secondarySystemBackground))
            TextField("Ví dụ: \\frac{1}{2} hoặc x^2", text: $latex, axis: .vertical)
                .font(.body.monospaced())
                .textInputAutocapitalization(.never)
                .autocorrectionDisabled()
                .lineLimit(1...4)
                .focused($focused)
                .padding(12)
                .accessibilityIdentifier("latexField")
            Divider()
            TemplateGallery { template in
                // Slots become empty groups, and #@ takes what was written so far.
                let current = latex.trimmingCharacters(in: .whitespaces)
                if template.contains("#@") {
                    latex = template.replacingOccurrences(of: "#@", with: current).replacingOccurrences(of: "#?", with: "")
                } else {
                    latex = current + template.replacingOccurrences(of: "#?", with: "")
                }
            }
            .padding(12)
        }
        .onAppear { focused = true }
    }

    @ViewBuilder
    private var preview: some View {
        let trimmed = latex.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty {
            Text("Gõ LaTeX hoặc chọn một mẫu bên dưới").font(.footnote).foregroundStyle(.secondary)
        } else if let math = MathRenderer.render(trimmed, fontSize: 26, color: .label, display: true) {
            ScrollView(.horizontal, showsIndicators: false) {
                Image(uiImage: math.image)
                    .containerRelativeFrame(.horizontal) { length, _ in max(length, math.image.size.width) }
            }
            .padding(.vertical, 12)
        } else {
            Label("Công thức chưa đúng cú pháp", systemImage: "exclamationmark.triangle")
                .font(.footnote).foregroundStyle(.orange)
        }
    }
}
