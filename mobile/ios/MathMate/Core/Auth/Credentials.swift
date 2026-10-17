import Foundation
import Security

/// Where the session token and the guest id live between launches.
protocol CredentialStore: AnyObject, Sendable {
    var token: String? { get set }
    var guestID: String? { get set }
}

/// The Keychain: the token and guest id survive app updates (and, for the guest id, a
/// reinstall on the same device), and never reach backups unencrypted.
final class KeychainCredentials: CredentialStore, @unchecked Sendable {
    private let service: String

    init(service: String = "com.tvcsoft.mathmate") {
        self.service = service
    }

    var token: String? {
        get { read("token") }
        set { write("token", newValue) }
    }

    var guestID: String? {
        get { read("guest-id") }
        set { write("guest-id", newValue) }
    }

    private func query(_ account: String) -> [String: Any] {
        [kSecClass as String: kSecClassGenericPassword,
         kSecAttrService as String: service,
         kSecAttrAccount as String: account]
    }

    private func read(_ account: String) -> String? {
        var query = query(account)
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne
        var result: AnyObject?
        guard SecItemCopyMatching(query as CFDictionary, &result) == errSecSuccess,
              let data = result as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    private func write(_ account: String, _ value: String?) {
        SecItemDelete(query(account) as CFDictionary)
        guard let value else { return }
        var item = query(account)
        item[kSecValueData as String] = Data(value.utf8)
        item[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlockThisDeviceOnly
        SecItemAdd(item as CFDictionary, nil)
    }
}

/// For tests and previews.
final class MemoryCredentials: CredentialStore, @unchecked Sendable {
    private let lock = NSLock()
    private var values: [String: String] = [:]

    init(token: String? = nil, guestID: String? = nil) {
        values["token"] = token
        values["guest"] = guestID
    }

    var token: String? {
        get { lock.withLock { values["token"] } }
        set { lock.withLock { values["token"] = newValue } }
    }

    var guestID: String? {
        get { lock.withLock { values["guest"] } }
        set { lock.withLock { values["guest"] = newValue } }
    }
}
