import Foundation
import Security

/// Хранит ключ ProxyAPI в Keychain. Ключ не в бинаре и не в исходниках —
/// юзер вводит один раз в настройках.
final class APIKeyStore {
    static let shared = APIKeyStore()

    private let service = "tech.mobiledeveloper.AgentChat"
    private let account = "PROXYAPI_KEY"

    private init() {}

    var key: String? { read() }

    var hasKey: Bool {
        guard let k = read() else { return false }
        return !k.isEmpty
    }

    /// Маска текущего ключа: 3 первых…3 последних. Сам ключ наружу не отдаём.
    var maskedKey: String? {
        guard let k = read(), !k.isEmpty else { return nil }
        guard k.count > 6 else { return String(repeating: "•", count: k.count) }
        return "\(k.prefix(3))…\(k.suffix(3))"
    }

    @discardableResult
    func save(_ value: String) -> Bool {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let data = trimmed.data(using: .utf8) else { return false }

        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        SecItemDelete(query as CFDictionary)

        var attributes = query
        attributes[kSecValueData as String] = data
        attributes[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock
        return SecItemAdd(attributes as CFDictionary, nil) == errSecSuccess
    }

    private func read() -> String? {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
            kSecReturnData as String: true,
            kSecMatchLimit as String: kSecMatchLimitOne
        ]
        var item: CFTypeRef?
        guard SecItemCopyMatching(query as CFDictionary, &item) == errSecSuccess,
              let data = item as? Data else { return nil }
        return String(data: data, encoding: .utf8)
    }

    func delete() {
        let query: [String: Any] = [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account
        ]
        SecItemDelete(query as CFDictionary)
    }
}
