import SwiftUI
import UIKit

/// A drawing to inspect: pinch to zoom, drag to pan, double-tap to zoom in or back, and
/// −/fit/+ buttons (web: drawing/ZoomImage.tsx).
struct ZoomableImage: View {
    let image: UIImage
    @State private var command: ZoomCommand?

    var body: some View {
        ZoomScrollView(image: image, command: $command)
            .background(Color.white)
            .clipShape(.rect(cornerRadius: 14))
            .overlay(RoundedRectangle(cornerRadius: 14).stroke(.separator, lineWidth: 0.5))
            .overlay(alignment: .topTrailing) {
                HStack(spacing: 2) {
                    zoomButton("minus.magnifyingglass", "Thu nhỏ", .zoomOut)
                    zoomButton("arrow.up.left.and.down.right.magnifyingglass", "Vừa khung", .fit)
                    zoomButton("plus.magnifyingglass", "Phóng to", .zoomIn)
                }
                .padding(4)
                .mmGlass(in: .capsule)
                .padding(10)
            }
            .accessibilityElement(children: .contain)
            .accessibilityIdentifier("drawingImage")
    }

    private func zoomButton(_ systemImage: String, _ label: String, _ action: ZoomCommand.Kind) -> some View {
        Button { command = ZoomCommand(kind: action) } label: {
            Image(systemName: systemImage).frame(width: 34, height: 30)
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
    }
}

struct ZoomCommand: Equatable {
    enum Kind { case zoomIn, zoomOut, fit }
    let kind: Kind
    let id = UUID()
}

private struct ZoomScrollView: UIViewRepresentable {
    let image: UIImage
    @Binding var command: ZoomCommand?

    func makeUIView(context: Context) -> FittingScrollView {
        let scroll = FittingScrollView()
        scroll.delegate = context.coordinator
        scroll.minimumZoomScale = 1
        scroll.maximumZoomScale = 6
        scroll.showsVerticalScrollIndicator = false
        scroll.showsHorizontalScrollIndicator = false
        scroll.bouncesZoom = true
        let imageView = UIImageView(image: image)
        imageView.contentMode = .scaleAspectFit
        imageView.isAccessibilityElement = true
        imageView.accessibilityLabel = "Hình vẽ"
        scroll.addSubview(imageView)
        scroll.imageView = imageView
        context.coordinator.imageView = imageView
        let doubleTap = UITapGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.doubleTapped))
        doubleTap.numberOfTapsRequired = 2
        scroll.addGestureRecognizer(doubleTap)
        return scroll
    }

    func updateUIView(_ scroll: FittingScrollView, context: Context) {
        let coordinator = context.coordinator
        if coordinator.imageView?.image !== image {
            coordinator.imageView?.image = image
            scroll.zoomScale = 1  // a new drawing (another version) starts fitted
        }
        scroll.setNeedsLayout()
        if let command, command.id != coordinator.lastCommand {
            coordinator.lastCommand = command.id
            switch command.kind {
            case .zoomIn: scroll.setZoomScale(min(scroll.zoomScale * 1.5, scroll.maximumZoomScale), animated: true)
            case .zoomOut: scroll.setZoomScale(max(scroll.zoomScale / 1.5, scroll.minimumZoomScale), animated: true)
            case .fit: scroll.setZoomScale(1, animated: true)
            }
        }
    }

    func makeCoordinator() -> Coordinator { Coordinator() }

    @MainActor
    final class Coordinator: NSObject, UIScrollViewDelegate {
        weak var imageView: UIImageView?
        var lastCommand: UUID?

        func viewForZooming(in scrollView: UIScrollView) -> UIView? { imageView }

        @objc func doubleTapped(_ gesture: UITapGestureRecognizer) {
            guard let scroll = gesture.view as? UIScrollView else { return }
            if scroll.zoomScale > 1 {
                scroll.setZoomScale(1, animated: true)
            } else {
                let point = gesture.location(in: imageView)
                let size = CGSize(width: scroll.bounds.width / 2.5, height: scroll.bounds.height / 2.5)
                scroll.zoom(to: CGRect(x: point.x - size.width / 2, y: point.y - size.height / 2,
                                       width: size.width, height: size.height), animated: true)
            }
        }
    }
}

/// Fits the image to its bounds whenever they change at zoom 1 (SwiftUI sizes the view after
/// updateUIView, so fitting there saw a zero size).
final class FittingScrollView: UIScrollView {
    weak var imageView: UIImageView?

    override func layoutSubviews() {
        super.layoutSubviews()
        guard let imageView, zoomScale == 1, bounds.width > 0 else { return }
        imageView.frame = CGRect(origin: .zero, size: bounds.size)
        contentSize = bounds.size
    }
}
