import SwiftUI

/// Phase 1 UI spike. `-screen inline|composer|sse` opens one screen (for simctl screenshots);
/// `-api http://127.0.0.1:8796` points the SSE screen at a server (web/e2e/server.py).
@main
struct UISpikeApp: App {
    var body: some Scene {
        WindowGroup { RootView() }
    }
}

struct RootView: View {
    private let defaults = UserDefaults.standard

    var body: some View {
        let api = URL(string: defaults.string(forKey: "api") ?? "http://127.0.0.1:8796")!
        let prompt = defaults.string(forKey: "prompt") ?? "Giải phương trình x + 1 = 3"
        switch defaults.string(forKey: "screen") {
        case "inline": InlineScreen()
        case "composer": ComposerScreen()
        case "sse": StreamingScreen(base: api, prompt: prompt)
        default:
            TabView {
                InlineScreen().tabItem { Label("Công thức", systemImage: "function") }
                ComposerScreen().tabItem { Label("Soạn tin", systemImage: "square.and.pencil") }
                StreamingScreen(base: api, prompt: prompt)
                    .tabItem { Label("SSE", systemImage: "antenna.radiowaves.left.and.right") }
            }
        }
    }
}
