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

    /// VisionKit calls these on the main thread.
    @MainActor
    final class Coordinator: NSObject, @preconcurrency VNDocumentCameraViewControllerDelegate {
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
