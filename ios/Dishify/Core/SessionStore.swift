import Foundation

@MainActor
final class AppRouter: ObservableObject {
    enum Page: Hashable {
        case welcome
        case login
        case register
        case cook
        case preferences
        case results
        case recipe(Int)
        case profile
    }

    @Published var page: Page = AccessTokenStore.load() == nil ? .welcome : .cook

    func go(_ page: Page) {
        self.page = page
    }
}

@MainActor
final class SessionStore: ObservableObject {
    @Published private(set) var token: String?
    @Published private(set) var user: UserProfile?
    @Published private(set) var isLoadingUser = false

    private var api: APIClient

    init() {
        self.api = APIClient()
        self.token = AccessTokenStore.load()

        api.onTokenRefreshed = { [weak self] accessToken, refreshToken in
            Task { @MainActor in
                AccessTokenStore.save(accessToken)
                if let refreshToken {
                    RefreshTokenStore.save(refreshToken)
                }
                self?.token = accessToken
            }
        }
        api.onRefreshFailed = { [weak self] in
            Task { @MainActor in
                self?.logout()
            }
        }

        if token != nil {
            Task { await loadUserOrLogout() }
        }
    }

    var isAuthenticated: Bool {
        token != nil
    }

    func login(username: String, password: String) async throws {
        let response = try await api.login(LoginRequest(username: username, password: password))
        AccessTokenStore.save(response.accessToken)
        if let rt = response.refreshToken {
            RefreshTokenStore.save(rt)
        }
        token = response.accessToken
        _ = try await loadUser()
    }

    func register(
        username: String,
        email: String,
        password: String,
        exclusionRestrictions: [String]
    ) async throws {
        _ = try await api.register(
            RegisterRequest(
                username: username,
                email: email,
                password: password,
                exclusionRestrictions: exclusionRestrictions
            )
        )
        try await login(username: username, password: password)
    }

    @discardableResult
    func loadUser() async throws -> UserProfile {
        isLoadingUser = true
        defer { isLoadingUser = false }
        let profile = try await api.me()
        user = profile
        return profile
    }

    func loadUserOrLogout() async {
        do {
            _ = try await loadUser()
        } catch {
            logout()
        }
    }

    func logout() {
        if let rt = RefreshTokenStore.load() {
            Task { try? await api.logout(rt) }
        }
        AccessTokenStore.clear()
        RefreshTokenStore.clear()
        token = nil
        user = nil
    }
}
