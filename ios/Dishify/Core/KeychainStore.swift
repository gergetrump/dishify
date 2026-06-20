import Foundation
import Security

struct StoredTokens: Codable, Equatable {
    let accessToken: String
    let refreshToken: String
    let expiresAt: Date

    init(accessToken: String, refreshToken: String, expiresIn: Int) {
        self.accessToken = accessToken
        self.refreshToken = refreshToken
        self.expiresAt = Date().addingTimeInterval(TimeInterval(expiresIn))
    }

    init(response: TokenResponse) {
        self.init(
            accessToken: response.accessToken,
            refreshToken: response.refreshToken,
            expiresIn: response.expiresIn
        )
    }

    var isExpiringSoon: Bool {
        expiresAt.timeIntervalSinceNow <= 30
    }
}

struct KeychainStore {
    private let service: String
    private let account: String

    init(service: String = "com.dishify.app", account: String = "auth.tokens") {
        self.service = service
        self.account = account
    }

    func save(_ tokens: StoredTokens) throws {
        let data = try JSONEncoder().encode(tokens)
        let query = baseQuery()

        SecItemDelete(query as CFDictionary)

        var attributes = query
        attributes[kSecValueData as String] = data
        attributes[kSecAttrAccessible as String] = kSecAttrAccessibleAfterFirstUnlock

        let status = SecItemAdd(attributes as CFDictionary, nil)
        guard status == errSecSuccess else {
            throw KeychainError.unhandledStatus(status)
        }
    }

    func load() -> StoredTokens? {
        var query = baseQuery()
        query[kSecReturnData as String] = true
        query[kSecMatchLimit as String] = kSecMatchLimitOne

        var item: CFTypeRef?
        let status = SecItemCopyMatching(query as CFDictionary, &item)

        guard status == errSecSuccess else {
            return nil
        }

        guard let data = item as? Data else {
            return nil
        }

        return try? JSONDecoder().decode(StoredTokens.self, from: data)
    }

    func delete() {
        SecItemDelete(baseQuery() as CFDictionary)
    }

    private func baseQuery() -> [String: Any] {
        [
            kSecClass as String: kSecClassGenericPassword,
            kSecAttrService as String: service,
            kSecAttrAccount as String: account,
        ]
    }
}

enum KeychainError: LocalizedError {
    case unhandledStatus(OSStatus)

    var errorDescription: String? {
        switch self {
        case .unhandledStatus(let status):
            return "Keychain operation failed with status \(status)."
        }
    }
}
