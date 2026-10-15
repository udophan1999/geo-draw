import SwiftUI
import UIKit

/// Images the API serves to the signed-in owner only, cached by their versioned URL
/// (`?v=` changes when a drawing is rendered again).
@MainActor
enum ImageStore {
    private static let cache = NSCache<NSString, UIImage>()

    static func image(at path: String, api: APIClient) async -> UIImage? {
        if let cached = cache.object(forKey: path as NSString) { return cached }
        guard let data = try? await api.file(at: path), let image = UIImage(data: data) else { return nil }
        cache.setObject(image, forKey: path as NSString)
        return image
    }
}

struct AuthImage: View {
    @Environment(SessionStore.self) private var session
    let path: String
    @State private var image: UIImage?
    @State private var failed = false

    var body: some View {
        Group {
            if let image {
                Image(uiImage: image).resizable().scaledToFit()
            } else if failed {
                Label("Không tải được ảnh", systemImage: "photo.badge.exclamationmark")
                    .font(.footnote).foregroundStyle(.secondary).padding()
            } else {
                ProgressView().frame(maxWidth: .infinity, minHeight: 120)
            }
        }
        .task(id: path) {
            image = await ImageStore.image(at: path, api: session.api)
            failed = image == nil
        }
    }
}

/// Photos sent to the tutor: at most 2048 px on the long side, JPEG (a phone photo can be
/// 10 MB; the server takes up to 20 MB, and OCR needs no more).
enum ImagePrep {
    static func prepare(_ data: Data) -> (data: Data, preview: UIImage)? {
        guard let image = UIImage(data: data) else { return nil }
        let longSide = max(image.size.width, image.size.height)
        let scale = min(1, 2048 / longSide)
        let size = CGSize(width: (image.size.width * scale).rounded(), height: (image.size.height * scale).rounded())
        let format = UIGraphicsImageRendererFormat.default()
        format.scale = 1
        let resized = UIGraphicsImageRenderer(size: size, format: format).image { _ in
            image.draw(in: CGRect(origin: .zero, size: size))
        }
        guard let jpeg = resized.jpegData(compressionQuality: 0.8) else { return nil }
        return (jpeg, resized)
    }
}
