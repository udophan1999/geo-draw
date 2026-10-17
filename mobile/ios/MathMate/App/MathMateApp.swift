import SwiftUI

/// Started by the UI tests (`-uiTesting`): credentials in memory, no password autofill.
enum UITesting {
    static let isActive = ProcessInfo.processInfo.arguments.contains("-uiTesting")
}

@main
struct MathMateApp: App {
    @State private var session: SessionStore
    @State private var conversations: ConversationsStore
    @State private var chat: ChatStore

    init() {
        let api = Self.makeAPI()
        let session = SessionStore(api: api)
        let conversations = ConversationsStore(api: api)
        let chat = ChatStore(api: api)
        // A finished turn may have renamed or created a conversation and used quota.
        chat.onTurnFinished = { [weak session, weak conversations] in
            await conversations?.load()
            await session?.refresh()
        }
        _session = State(initialValue: session)
        _conversations = State(initialValue: conversations)
        _chat = State(initialValue: chat)
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
                .environment(chat)
        }
    }
}

struct RootView: View {
    @Environment(SessionStore.self) private var session
    @Environment(ConversationsStore.self) private var conversations
    @Environment(ChatStore.self) private var chat

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
        .onChange(of: session.user?.id) {
            conversations.reset()
            chat.reset()
        }
    }
}

/// The list and the open conversation: side by side on iPad, a stack on iPhone.
struct MainView: View {
    /// The selection for a new conversation. A split view shows its detail on iPhone only for a
    /// non-nil selection, so "new" cannot be nil.
    static let newConversation = "new"

    @Environment(ConversationsStore.self) private var conversations
    @Environment(ChatStore.self) private var chat
    @Environment(\.scenePhase) private var scenePhase
    @State private var selection: String?
    @State private var showingSettings = false
    @State private var columns = NavigationSplitViewVisibility.automatic

    var body: some View {
        NavigationSplitView(columnVisibility: $columns) {
            ConversationListView(selection: $selection,
                                 onNew: { selection = Self.newConversation },
                                 onSettings: { showingSettings = true })
        } detail: {
            NavigationStack {
                ChatView(conversationId: selection == Self.newConversation ? nil : selection) { created in
                    selection = created
                    Task { await conversations.load() }
                }
                .id(selection ?? "new")
            }
        }
        .sheet(isPresented: $showingSettings) { SettingsView() }
        .task { if !conversations.loaded { await conversations.load() } }
        // Back from the background: jobs that ended meanwhile are on the server.
        .onChange(of: scenePhase) {
            guard scenePhase == .active else { return }
            Task {
                await conversations.load()
                if let selection, selection != Self.newConversation { await chat.load(selection) }
            }
        }
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
