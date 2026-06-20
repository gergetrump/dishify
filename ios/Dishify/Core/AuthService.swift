import AuthenticationServices
import CryptoKit
import Foundation
import UIKit

enum PKCEGenerator {
    static func codeVerifier(length: Int = 64) -> String {
        let charset = Array("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~")
        var bytes = [UInt8](repeating: 0, count: length)
        _ = SecRandomCopyBytes(kSecRandomDefault, bytes.count, &bytes)
        return String(bytes.map { charset[Int($0) % charset.count] })
    }

    static func codeChallenge(for verifier: String) -> String {
        let hash = SHA256.hash(data: Data(verifier.utf8))
        return base64URLEncode(Data(hash))
    }

    private static func base64URLEncode(_ data: Data) -> String {
        data.base64EncodedString()
            .replacingOccurrences(of: "+", with: "-")
            .replacingOccurrences(of: "/", with: "_")
            .replacingOccurrences(of: "=", with: "")
    }
}

final class AccessTokenHolder: @unchecked Sendable {
    private var token: String?

    func get() -> String? {
        token
    }

    func set(_ token: String?) {
        self.token = token
    }
}

enum AuthError: LocalizedError {
    case missingConfiguration
    case signInCancelled
    case missingAuthorizationCode
    case tokenExchangeFailed(String)
    case refreshFailed(String)
    case noStoredSession

    var errorDescription: String? {
        switch self {
        case .missingConfiguration:
            return "Authentication configuration is unavailable."
        case .signInCancelled:
            return "Sign in was cancelled."
        case .missingAuthorizationCode:
            return "Authorization code was missing from the callback."
        case .tokenExchangeFailed(let message):
            return "Token exchange failed: \(message)"
        case .refreshFailed(let message):
            return "Token refresh failed: \(message)"
        case .noStoredSession:
            return "No stored authentication session."
        }
    }
}

@MainActor
final class AuthService: NSObject, ObservableObject {
    @Published private(set) var isSignedIn = false

    private let apiClient: APIClient
    private let keychain: KeychainStore
    private let session: URLSession
    private let callbackScheme: String

    private var authConfig: AuthConfig?
    private var cachedTokens: StoredTokens?
    private var refreshTask: Task<StoredTokens, Error>?
    private let tokenHolder = AccessTokenHolder()

    init(
        apiClient: APIClient = APIClient(),
        keychain: KeychainStore = KeychainStore(),
        session: URLSession = Config.apiSession,
        callbackScheme: String = "dishify"
    ) {
        self.apiClient = apiClient
        self.keychain = keychain
        self.session = session
        self.callbackScheme = callbackScheme
        super.init()
        restoreSession()
    }

    func restoreSession() {
        cachedTokens = keychain.load()
        tokenHolder.set(cachedTokens?.accessToken)
        isSignedIn = cachedTokens != nil
    }

    func signIn() async throws {
        let config = try await loadAuthConfig()
        let verifier = PKCEGenerator.codeVerifier()
        let challenge = PKCEGenerator.codeChallenge(for: verifier)
        let authorizationURL = try makeAuthorizationURL(config: config, challenge: challenge)
        let callbackURL = try await startWebAuthentication(url: authorizationURL)

        guard let code = URLComponents(url: callbackURL, resolvingAgainstBaseURL: false)?
            .queryItems?
            .first(where: { $0.name == "code" })?
            .value else {
            throw AuthError.missingAuthorizationCode
        }

        let tokenResponse = try await exchangeAuthorizationCode(
            code,
            verifier: verifier,
            config: config
        )
        try persist(tokenResponse)
    }

    func signIn(username: String, password: String) async throws {
        let response: TokenResponse = try await apiClient.request(
            "/auth/login",
            method: .post,
            body: LoginRequest(username: username, password: password)
        )
        try persist(response)
    }

    func refresh() async throws {
        _ = try await refreshIfNeeded(force: true)
    }

    func currentAccessToken() async throws -> String? {
        guard let tokens = try await refreshIfNeeded(force: false) else {
            return nil
        }
        return tokens.accessToken
    }

    func forceRefreshAccessToken() async throws -> String? {
        guard let tokens = try await refreshIfNeeded(force: true) else {
            return nil
        }
        return tokens.accessToken
    }

    var accessTokenHolder: AccessTokenHolder {
        tokenHolder
    }

    var syncAccessToken: String? {
        tokenHolder.get()
    }

    func signOut() {
        refreshTask?.cancel()
        refreshTask = nil
        cachedTokens = nil
        tokenHolder.set(nil)
        isSignedIn = false
        keychain.delete()
    }

    func makeAPIClient() -> APIClient {
        let holder = tokenHolder
        return APIClient(tokenProvider: { holder.get() })
    }

    private func loadAuthConfig() async throws -> AuthConfig {
        if let authConfig {
            return authConfig
        }

        let config: AuthConfig = try await apiClient.request("/auth/config")
        authConfig = config
        return config
    }

    private func makeAuthorizationURL(config: AuthConfig, challenge: String) throws -> URL {
        guard var components = URLComponents(string: config.authorizationEndpoint) else {
            throw AuthError.missingConfiguration
        }

        components.queryItems = [
            URLQueryItem(name: "client_id", value: Config.iosClientID),
            URLQueryItem(name: "redirect_uri", value: Config.redirectURI),
            URLQueryItem(name: "response_type", value: "code"),
            URLQueryItem(name: "scope", value: "openid profile email"),
            URLQueryItem(name: "code_challenge", value: challenge),
            URLQueryItem(name: "code_challenge_method", value: "S256"),
        ]

        guard let url = components.url else {
            throw AuthError.missingConfiguration
        }

        return url
    }

    private func startWebAuthentication(url: URL) async throws -> URL {
        try await withCheckedThrowingContinuation { continuation in
            let session = ASWebAuthenticationSession(
                url: url,
                callbackURLScheme: callbackScheme
            ) { callbackURL, error in
                if let error {
                    if (error as? ASWebAuthenticationSessionError)?.code == .canceledLogin {
                        continuation.resume(throwing: AuthError.signInCancelled)
                    } else {
                        continuation.resume(throwing: error)
                    }
                    return
                }

                guard let callbackURL else {
                    continuation.resume(throwing: AuthError.missingAuthorizationCode)
                    return
                }

                continuation.resume(returning: callbackURL)
            }

            session.presentationContextProvider = self
            session.prefersEphemeralWebBrowserSession = false

            if !session.start() {
                continuation.resume(throwing: AuthError.missingConfiguration)
            }
        }
    }

    private func exchangeAuthorizationCode(
        _ code: String,
        verifier: String,
        config: AuthConfig
    ) async throws -> TokenResponse {
        try await requestTokens(
            endpoint: config.tokenEndpoint,
            parameters: [
                "grant_type": "authorization_code",
                "client_id": Config.iosClientID,
                "code": code,
                "redirect_uri": Config.redirectURI,
                "code_verifier": verifier,
            ],
            failure: AuthError.tokenExchangeFailed
        )
    }

    private func refreshTokens(_ tokens: StoredTokens, config: AuthConfig) async throws -> TokenResponse {
        try await requestTokens(
            endpoint: config.tokenEndpoint,
            parameters: [
                "grant_type": "refresh_token",
                "client_id": Config.iosClientID,
                "refresh_token": tokens.refreshToken,
            ],
            failure: AuthError.refreshFailed
        )
    }

    private func requestTokens(
        endpoint: String,
        parameters: [String: String],
        failure: (String) -> AuthError
    ) async throws -> TokenResponse {
        guard let url = URL(string: endpoint) else {
            throw AuthError.missingConfiguration
        }

        var request = URLRequest(url: url)
        request.httpMethod = "POST"
        request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
        request.httpBody = formEncodedBody(parameters)

        let data: Data
        let response: URLResponse

        do {
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.transport(error)
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.transport(URLError(.badServerResponse))
        }

        let body = String(data: data, encoding: .utf8) ?? ""

        guard (200 ... 299).contains(httpResponse.statusCode) else {
            throw failure(body.isEmpty ? "HTTP \(httpResponse.statusCode)" : body)
        }

        do {
            return try JSONDecoder().decode(TokenResponse.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    private func persist(_ tokenResponse: TokenResponse) throws {
        let tokens = StoredTokens(response: tokenResponse)
        try keychain.save(tokens)
        cachedTokens = tokens
        tokenHolder.set(tokens.accessToken)
        isSignedIn = true
    }

    private func refreshIfNeeded(force: Bool) async throws -> StoredTokens? {
        guard let stored = cachedTokens ?? keychain.load() else {
            return nil
        }

        if !force && !stored.isExpiringSoon {
            cachedTokens = stored
            tokenHolder.set(stored.accessToken)
            isSignedIn = true
            return stored
        }

        if let refreshTask {
            return try await refreshTask.value
        }

        let task = Task { () throws -> StoredTokens in
            let config = try await loadAuthConfig()
            let response = try await refreshTokens(stored, config: config)
            let refreshed = StoredTokens(response: response)
            try keychain.save(refreshed)
            return refreshed
        }

        refreshTask = task
        defer { refreshTask = nil }

        do {
            let refreshed = try await task.value
            cachedTokens = refreshed
            tokenHolder.set(refreshed.accessToken)
            isSignedIn = true
            return refreshed
        } catch {
            if force || stored.isExpiringSoon {
                signOut()
            }
            throw error
        }
    }

    private func formEncodedBody(_ parameters: [String: String]) -> Data {
        parameters
            .map { key, value in
                "\(formEncode(key))=\(formEncode(value))"
            }
            .joined(separator: "&")
            .data(using: .utf8) ?? Data()
    }

    private func formEncode(_ value: String) -> String {
        value.addingPercentEncoding(withAllowedCharacters: .urlQueryAllowed) ?? value
    }
}

extension AuthService: ASWebAuthenticationPresentationContextProviding {
    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .flatMap(\.windows)
            .first(where: \.isKeyWindow) ?? ASPresentationAnchor()
    }
}
