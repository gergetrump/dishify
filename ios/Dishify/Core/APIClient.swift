import Foundation

enum HTTPMethod: String {
    case get = "GET"
    case post = "POST"
    case put = "PUT"
}

enum APIError: Error, LocalizedError {
    case auth
    case validation(String)
    case unavailable(String?)
    case network(Error)
    case decoding(Error)
    case http(Int, String)

    var errorDescription: String? {
        switch self {
        case .auth:
            return "Your session is missing or expired. Log in again."
        case .validation(let message):
            return message
        case .unavailable(let detail):
            return detail ?? "Dishify is not ready yet. Check backend services and indexing."
        case .network:
            return "Could not reach the Dishify API. Check that the backend is running."
        case .decoding(let error):
            return "Could not read the API response: \(error.localizedDescription)"
        case .http(_, let message):
            return message
        }
    }
}

struct APIClient {
    var baseURL: URL = Config.apiBaseURL
    var tokenProvider: () -> String? = { AccessTokenStore.load() }
    var refreshTokenProvider: () -> String? = { RefreshTokenStore.load() }
    var onTokenRefreshed: ((String, String?) -> Void)?
    var onRefreshFailed: (() -> Void)?
    var session: URLSession = Config.apiSession
    var decoder = JSONDecoder()
    var encoder = JSONEncoder()

    func health() async throws -> HealthResponse {
        try await request("/health", skipAuth: true)
    }

    func register(_ body: RegisterRequest) async throws -> RegisterResponse {
        try await request("/auth/register", method: .post, body: body, skipAuth: true)
    }

    func login(_ body: LoginRequest) async throws -> TokenResponse {
        try await request("/auth/login", method: .post, body: body, skipAuth: true)
    }

    func refreshToken(_ refreshToken: String) async throws -> TokenResponse {
        try await rawRequest("/auth/refresh", method: .post, body: RefreshTokenBody(refreshToken: refreshToken), skipAuth: true)
    }

    func logout(_ refreshToken: String) async throws {
        _ = try await performRequest("/auth/logout", method: .post, body: RefreshTokenBody(refreshToken: refreshToken), skipAuth: true)
    }

    func me() async throws -> UserProfile {
        try await request("/me")
    }

    func preferences() async throws -> UserPreferences {
        try await request("/me/preferences")
    }

    func updatePreferences(_ body: UpdatePreferencesRequest) async throws -> UserPreferences {
        try await request("/me/preferences", method: .put, body: body)
    }

    func recommend(_ body: RecommendRequest) async throws -> RecommendResponse {
        try await request("/recommend", method: .post, body: body)
    }

    private func request<T: Decodable>(
        _ path: String,
        method: HTTPMethod = .get,
        body: Encodable? = nil,
        skipAuth: Bool = false
    ) async throws -> T {
        do {
            return try await rawRequest(path, method: method, body: body, skipAuth: skipAuth)
        } catch APIError.auth where !skipAuth {
            if await tryRefresh() {
                return try await rawRequest(path, method: method, body: body, skipAuth: skipAuth)
            }
            throw APIError.auth
        }
    }

    private func tryRefresh() async -> Bool {
        guard let rt = refreshTokenProvider() else {
            onRefreshFailed?()
            return false
        }
        do {
            let tokens = try await refreshToken(rt)
            onTokenRefreshed?(tokens.accessToken, tokens.refreshToken)
            return true
        } catch {
            onRefreshFailed?()
            return false
        }
    }

    private func rawRequest<T: Decodable>(
        _ path: String,
        method: HTTPMethod = .get,
        body: Encodable? = nil,
        skipAuth: Bool = false
    ) async throws -> T {
        let data = try await performRequest(path, method: method, body: body, skipAuth: skipAuth)
        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    private func performRequest(
        _ path: String,
        method: HTTPMethod,
        body: Encodable?,
        skipAuth: Bool
    ) async throws -> Data {
        guard let url = URL(string: path, relativeTo: baseURL)?.absoluteURL else {
            throw APIError.http(0, "Bad API URL.")
        }

        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        if let body {
            request.httpBody = try encoder.encode(AnyEncodable(body))
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        if !skipAuth, let token = tokenProvider(), !token.isEmpty {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        let data: Data
        let response: URLResponse
        do {
            #if DEBUG
            print("[API] \(method.rawValue) \(url.absoluteString)")
            #endif
            (data, response) = try await session.data(for: request)
        } catch {
            throw APIError.network(error)
        }

        guard let httpResponse = response as? HTTPURLResponse else {
            throw APIError.http(0, "Bad server response.")
        }

        guard (200 ... 299).contains(httpResponse.statusCode) else {
            throw makeAPIError(status: httpResponse.statusCode, data: data)
        }

        return data
    }

    private func makeAPIError(status: Int, data: Data) -> APIError {
        let detail = Self.detailText(from: data)
        switch status {
        case 401:
            return .auth
        case 422:
            return .validation(detail ?? "Some fields need attention before Dishify can continue.")
        case 503:
            return .unavailable(detail)
        default:
            return .http(status, detail ?? "Something went wrong. Try again.")
        }
    }

    private static func detailText(from data: Data) -> String? {
        guard !data.isEmpty else { return nil }
        guard let object = try? JSONSerialization.jsonObject(with: data) else {
            return String(data: data, encoding: .utf8)
        }
        guard let dict = object as? [String: Any] else { return nil }
        if let detail = dict["detail"] as? String { return detail }
        if let message = dict["message"] as? String { return message }
        if let details = dict["detail"] as? [[String: Any]] {
            let messages = details.compactMap { $0["msg"] as? String }
            return messages.isEmpty ? nil : messages.joined(separator: " ")
        }
        return nil
    }
}

struct RefreshTokenBody: Codable {
    let refreshToken: String

    enum CodingKeys: String, CodingKey {
        case refreshToken = "refresh_token"
    }
}

private struct AnyEncodable: Encodable {
    private let encodeClosure: (Encoder) throws -> Void

    init(_ value: Encodable) {
        self.encodeClosure = value.encode
    }

    func encode(to encoder: Encoder) throws {
        try encodeClosure(encoder)
    }
}
