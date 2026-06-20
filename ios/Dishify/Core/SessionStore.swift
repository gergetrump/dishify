import Foundation

enum SessionState: Equatable {
    case unknown
    case signedOut
    case signedIn(UserProfile?)
}

@MainActor
final class SessionStore: ObservableObject {
    @Published private(set) var state: SessionState = .unknown
    @Published private(set) var isLoading = false
    @Published var errorMessage: String?

    private let authService: AuthService
    private let apiClient: APIClient
    private var tokenRefreshTask: Task<Void, Never>?

    init(authService: AuthService? = nil) {
        self.authService = authService ?? AuthService()
        self.apiClient = APIClient()
    }

    var currentProfile: UserProfile? {
        if case .signedIn(let profile) = state {
            return profile
        }
        return nil
    }

    func bootstrap() async {
        guard case .unknown = state else { return }

        isLoading = true
        defer { isLoading = false }

        authService.restoreSession()

        guard authService.isSignedIn else {
            state = .signedOut
            return
        }

        await restoreSignedInSession()
    }

    func signIn() async {
        await performAuthOperation { try await authService.signIn() }
    }

    func signIn(username: String, password: String) async {
        let trimmedUsername = username.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedPassword = password.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !trimmedUsername.isEmpty, !trimmedPassword.isEmpty else {
            errorMessage = "Enter a username and password."
            return
        }

        await performAuthOperation {
            try await authService.signIn(username: trimmedUsername, password: trimmedPassword)
        }
    }

    func register(username: String, email: String, password: String) async {
        let trimmedUsername = username.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedEmail = email.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedPassword = password.trimmingCharacters(in: .whitespacesAndNewlines)

        guard !trimmedUsername.isEmpty, !trimmedEmail.isEmpty, !trimmedPassword.isEmpty else {
            errorMessage = "Enter a username, email, and password."
            return
        }

        await performAuthOperation {
            let _: RegisterResponse = try await apiClient.request(
                "/auth/register",
                method: .post,
                body: RegisterRequest(
                    username: trimmedUsername,
                    email: trimmedEmail,
                    password: trimmedPassword,
                    exclusionRestrictions: nil
                )
            )
            try await authService.signIn(username: trimmedUsername, password: trimmedPassword)
        }
    }

    func signOut() {
        tokenRefreshTask?.cancel()
        tokenRefreshTask = nil
        authService.signOut()
        state = .signedOut
        errorMessage = nil
    }

    func makeAuthenticatedClient() async throws -> APIClient {
        guard try await authService.currentAccessToken() != nil else {
            signOut()
            throw APIError.unauthorized
        }

        let tokenHolder = authService.accessTokenHolder
        let authService = self.authService

        return APIClient(
            tokenProvider: { tokenHolder.get() },
            tokenRefresher: {
                try await Task { @MainActor in
                    try await authService.forceRefreshAccessToken()
                }.value
            },
            onUnauthorized: { [weak self] in
                await MainActor.run {
                    self?.signOut()
                }
            }
        )
    }

    func message(for error: Error, context: APIError.Context = .general) -> String {
        if let apiError = error as? APIError {
            return apiError.userMessage(for: context)
        }
        return error.localizedDescription
    }

    private func performAuthOperation(_ operation: () async throws -> Void) async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }

        do {
            try await operation()
            await restoreSignedInSession()
        } catch AuthError.signInCancelled {
            return
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func restoreSignedInSession() async {
        do {
            let profile = try await fetchProfile()
            state = .signedIn(profile)
            startProactiveTokenRefresh()
        } catch {
            signOut()
            errorMessage = message(for: error)
        }
    }

    private func fetchProfile() async throws -> UserProfile {
        let client = try await makeAuthenticatedClient()
        return try await client.request("/me", requiresAuth: true)
    }

    private func startProactiveTokenRefresh() {
        tokenRefreshTask?.cancel()
        tokenRefreshTask = Task { [weak self] in
            while !Task.isCancelled {
                try? await Task.sleep(for: .seconds(60))
                guard !Task.isCancelled else { return }
                _ = try? await self?.authService.currentAccessToken()
            }
        }
    }
}
