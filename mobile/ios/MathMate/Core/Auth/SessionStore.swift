import Foundation
import Observation

/// Who is using the app and which screen they may see. Mirrors the web's AppLayout guard and
/// lib/guest.ts: without an account, the app opens on the welcome screen unless the student
/// chose "Dùng thử" before.
@MainActor
@Observable
final class SessionStore {
    enum Phase: Equatable {
        case loading
        /// This build is older than the server's `min_ios_build`.
        case updateRequired(storeURL: URL?)
        case welcome
        case ready
    }

    private(set) var phase: Phase = .loading
    private(set) var me: Me?
    /// Shown on the welcome screen when the server could not be reached at launch.
    private(set) var startError: String?

    let api: APIClient
    private let defaults: UserDefaults
    private static let guestModeKey = "guest-mode"

    init(api: APIClient, defaults: UserDefaults = .standard) {
        self.api = api
        self.defaults = defaults
    }

    var user: User? { me?.user }
    var isGuest: Bool { me?.user == nil }

    private var guestMode: Bool {
        get { defaults.bool(forKey: Self.guestModeKey) }
        set { defaults.set(newValue, forKey: Self.guestModeKey) }
    }

    /// The build number in Info.plist (CFBundleVersion).
    static var build: Int {
        (Bundle.main.object(forInfoDictionaryKey: "CFBundleVersion") as? String).flatMap(Int.init) ?? 0
    }

    func start() async {
        phase = .loading
        startError = nil
        if let config = try? await api.appConfig(), Self.build < config.minIosBuild {
            phase = .updateRequired(storeURL: config.iosStoreUrl.flatMap(URL.init(string:)))
            return
        }
        do {
            me = try await api.me()
            if me?.user == nil && api.isSignedIn {
                await api.logout()  // the session ended on the server (expired, account locked…)
            }
        } catch {
            startError = error.localizedDescription
        }
        phase = (me?.user != nil || guestMode) && me != nil ? .ready : .welcome
    }

    func refresh() async {
        if let fresh = try? await api.me() { me = fresh }
    }

    func login(username: String, password: String) async throws {
        me = try await api.login(username: username, password: password)
        guestMode = false
        phase = .ready
    }

    func register(username: String, password: String) async throws {
        me = try await api.register(username: username, password: password)
        guestMode = false
        phase = .ready
    }

    func continueAsGuest() async {
        guestMode = true
        if me == nil { await refresh() }
        phase = me == nil ? .welcome : .ready
    }

    /// A guest who wants to sign in: back to the welcome screen, keeping the guest id.
    func showWelcome() {
        guestMode = false
        phase = .welcome
    }

    func logout() async {
        await api.logout()
        guestMode = false
        me = nil
        await refresh()
        phase = .welcome
    }

    func deleteAccount(password: String) async throws {
        try await api.deleteAccount(password: password)
        guestMode = false
        me = nil
        await refresh()
        phase = .welcome
    }
}
