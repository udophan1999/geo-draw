import SwiftUI

/// Started by the UI tests (`-uiTesting`): credentials in memory, no password autofill.
enum UITesting {
    static let isActive = ProcessInfo.processInfo.arguments.contains("-uiTesting")
}

@main
struct MathMateApp: App {
    @State private var session: SessionStore
    @State private var conversations: ConversationsStore

    init() {
        let api = Self.makeAPI()
        _session = State(initialValue: SessionStore(api: api))
        _conversations = State(initialValue: ConversationsStore(api: api))
    }

    /// UI tests start from a clean slate and may point the app at another server:
    /// `-uiTesting` keeps credentials in memory, `-api <url>` overrides the base URL.
    private static func makeAPI() -> APIClient {
        let defaults = UserDefaults.standard
        let testing = UITesting.isActive
        let credentials: CredentialStore = testing ? MemoryCredentials() : KeychainCredentials()
        if testing { defaults.removeObject(forKey: "guest-mode") }
        if let url = defaults.string(forKey: "api").flatMap(URL.init(string:)) {
            return APIClient(baseURL: url, credentials: credentials)
        }
        return .configured(credentials: credentials)
    }

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(session)
                .environment(conversations)
        }
    }
}

struct RootView: View {
    @Environment(SessionStore.self) private var session
    @Environment(ConversationsStore.self) private var conversations

    var body: some View {
        Group {
            switch session.phase {
            case .loading:
                ProgressView().controlSize(.large)
            case .updateRequired(let storeURL):
                UpdateRequiredView(storeURL: storeURL)
            case .welcome:
                WelcomeView()
            case .ready:
                MainView()
            }
        }
        .animation(.default, value: session.phase)
        .task { await session.start() }
        .onChange(of: session.user?.id) { conversations.reset() }
    }
}

/// The list and the open conversation: side by side on iPad, a stack on iPhone.
struct MainView: View {
    @Environment(ConversationsStore.self) private var conversations
    @State private var selection: String?
    @State private var showingSettings = false
    @State private var columns = NavigationSplitViewVisibility.automatic

    var body: some View {
        NavigationSplitView(columnVisibility: $columns) {
            ConversationListView(selection: $selection,
                                 onNew: { selection = nil },
                                 onSettings: { showingSettings = true })
        } detail: {
            NavigationStack {
                if let selection {
                    ConversationView(id: selection)
                } else {
                    NewConversationView()
                }
            }
        }
        .sheet(isPresented: $showingSettings) { SettingsView() }
        .task { if !conversations.loaded { await conversations.load() } }
    }
}

/// This build is too old for the server (GET /api/app-config).
struct UpdateRequiredView: View {
    let storeURL: URL?

    var body: some View {
        ContentUnavailableView {
            Label("Cập nhật \(Brand.appName)", systemImage: "arrow.down.app")
        } description: {
            Text("Phiên bản này đã cũ. Hãy cập nhật để tiếp tục học cùng \(Brand.appName).")
        } actions: {
            if let storeURL {
                Link("Mở App Store", destination: storeURL).mmGlassButton(prominent: true)
            }
        }
    }
}
