import SwiftUI
import UIKit
import VisionKit

/// Common symbols as Unicode, one tap each (web: chat/MathInput.tsx SymbolBar).
struct SymbolBar: View {
    let onInsert: (String) -> Void

    var body: some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 6) {
                ForEach(SharedData.symbols, id: \.self) { symbol in
                    Button {
                        Haptics.selection()
                        onInsert(symbol.symbol)
                    } label: {
                        Text(symbol.symbol)
                            .font(.body)
                            .frame(minWidth: 34, minHeight: 34)
                    }
                    .buttonStyle(.plain)
                    .background(Color(.secondarySystemFill), in: .rect(cornerRadius: 8))
                    .accessibilityLabel(symbol.name)
                }
            }
            .padding(.horizontal, 2)
        }
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Ký hiệu toán")
        .accessibilityIdentifier("symbolBar")
    }
}

/// Writing a formula: LaTeX with a live preview and the gallery of templates. A stand-in for
/// the visual editor of phase 5 (docs/mobile-ios-plan.md §8).
struct FormulaSheet: View {
    @Environment(\.dismiss) private var dismiss
    let initialLatex: String
    let editingExisting: Bool
    let onDone: (String) -> Void

    @State private var latex = ""
    @State private var group = SharedData.formulaGroups.first?.id ?? ""
    @FocusState private var focused: Bool

    var body: some View {
        NavigationStack {
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
                gallery
            }
            .navigationTitle(editingExisting ? "Sửa công thức" : "Công thức")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Hủy") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button(editingExisting ? "Lưu" : "Chèn") {
                        onDone(latex.trimmingCharacters(in: .whitespacesAndNewlines))
                        dismiss()
                    }
                    .disabled(latex.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                    .accessibilityIdentifier("insertFormula")
                }
            }
        }
        .onAppear {
            latex = initialLatex
            focused = true
        }
    }

    @ViewBuilder
    private var preview: some View {
        let trimmed = latex.trimmingCharacters(in: .whitespacesAndNewlines)
        if trimmed.isEmpty {
            Text("Chọn một mẫu bên dưới hoặc gõ LaTeX").font(.footnote).foregroundStyle(.secondary)
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

    private var gallery: some View {
        VStack(spacing: 8) {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 6) {
                    ForEach(SharedData.formulaGroups) { item in
                        Button(item.name) { group = item.id }
                            .font(.footnote.weight(.medium))
                            .padding(.horizontal, 10).padding(.vertical, 6)
                            .foregroundStyle(group == item.id ? Color.white : .primary)
                            .background(group == item.id ? Brand.primary : Color(.secondarySystemFill), in: .capsule)
                    }
                }
                .padding(.horizontal, 12)
            }
            .padding(.top, 10)
            ScrollView {
                let current = SharedData.formulaGroups.first { $0.id == group }
                LazyVGrid(columns: [GridItem(.adaptive(minimum: current?.wide == true ? 160 : 72), spacing: 8)], spacing: 8) {
                    ForEach(current?.items ?? [], id: \.self) { template in
                        Button { add(template) } label: { TemplateTile(template: template) }
                            .buttonStyle(.plain)
                            .accessibilityLabel(template.label)
                    }
                }
                .padding(12)
            }
        }
    }

    /// Adds a template at the end: its slots become empty groups to fill in, and `#@`
    /// takes what was written so far (as the web's gallery does with the selection).
    private func add(_ template: SharedData.Template) {
        Haptics.selection()
        var snippet = template.latex
        let current = latex.trimmingCharacters(in: .whitespaces)
        if snippet.contains("#@") {
            snippet = snippet.replacingOccurrences(of: "#@", with: current)
            latex = snippet.replacingOccurrences(of: "#?", with: "")
        } else {
            latex = current + snippet.replacingOccurrences(of: "#?", with: "")
        }
    }
}

private struct TemplateTile: View {
    let template: SharedData.Template

    var body: some View {
        // \square is SwiftMath's empty-slot box.
        let latex = template.latex.replacingOccurrences(of: "#?", with: "\\square ").replacingOccurrences(of: "#@", with: "\\square ")
        Group {
            if let math = MathRenderer.render(latex, fontSize: 18, color: .label) {
                Image(uiImage: math.image).resizable().scaledToFit().frame(maxHeight: 34)
            } else {
                Text(template.label).font(.caption)
            }
        }
        .frame(maxWidth: .infinity, minHeight: 52)
        .padding(.horizontal, 6)
        .background(Color(.secondarySystemBackground), in: .rect(cornerRadius: 10))
    }
}

/// Photographing a problem: VisionKit's document camera finds the page, crops and flattens it.
struct DocumentScanner: UIViewControllerRepresentable {
    let onScan: (UIImage) -> Void
    @Environment(\.dismiss) private var dismiss

    static var isAvailable: Bool { VNDocumentCameraViewController.isSupported }

    func makeUIViewController(context: Context) -> VNDocumentCameraViewController {
        let controller = VNDocumentCameraViewController()
        controller.delegate = context.coordinator
        return controller
    }

    func updateUIViewController(_ controller: VNDocumentCameraViewController, context: Context) {}

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    final class Coordinator: NSObject, VNDocumentCameraViewControllerDelegate {
        private let parent: DocumentScanner
        init(_ parent: DocumentScanner) { self.parent = parent }

        func documentCameraViewController(_ controller: VNDocumentCameraViewController, didFinishWith scan: VNDocumentCameraScan) {
            // One problem per message: the first page.
            if scan.pageCount > 0 { parent.onScan(scan.imageOfPage(at: 0)) }
            parent.dismiss()
        }

        func documentCameraViewControllerDidCancel(_ controller: VNDocumentCameraViewController) { parent.dismiss() }

        func documentCameraViewController(_ controller: VNDocumentCameraViewController, didFailWithError error: Error) {
            parent.dismiss()
        }
    }
}
