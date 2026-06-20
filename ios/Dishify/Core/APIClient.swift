import Foundation

enum HTTPMethod: String {
    case get = "GET"
    case post = "POST"
    case put = "PUT"
}

typealias AccessTokenProvider = @Sendable () -> String?
typealias AccessTokenRefresher = @Sendable () async throws -> String?
typealias UnauthorizedHandler = @Sendable () async -> Void

struct APIClient {
    let baseURL: URL
    let session: URLSession
    let tokenProvider: AccessTokenProvider?
    let tokenRefresher: AccessTokenRefresher?
    let onUnauthorized: UnauthorizedHandler?
    let decoder: JSONDecoder
    let encoder: JSONEncoder

    init(
        baseURL: URL = Config.apiBaseURL,
        session: URLSession = Config.apiSession,
        tokenProvider: AccessTokenProvider? = nil,
        tokenRefresher: AccessTokenRefresher? = nil,
        onUnauthorized: UnauthorizedHandler? = nil,
        decoder: JSONDecoder = JSONDecoder(),
        encoder: JSONEncoder = JSONEncoder()
    ) {
        self.baseURL = baseURL
        self.session = session
        self.tokenProvider = tokenProvider
        self.tokenRefresher = tokenRefresher
        self.onUnauthorized = onUnauthorized
        self.decoder = decoder
        self.encoder = encoder
    }

    func health() async throws -> HealthResponse {
        try await request("/health")
    }

    func request<T: Decodable>(
        _ path: String,
        method: HTTPMethod = .get,
        body: Data? = nil,
        requiresAuth: Bool = false
    ) async throws -> T {
        let data = try await performRequest(
            path,
            method: method,
            body: body,
            requiresAuth: requiresAuth,
            didRetryAfterUnauthorized: false
        )

        do {
            return try decoder.decode(T.self, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    func request<T: Decodable, Body: Encodable>(
        _ path: String,
        method: HTTPMethod,
        body: Body,
        requiresAuth: Bool = false
    ) async throws -> T {
        let encodedBody = try encoder.encode(body)
        return try await request(path, method: method, body: encodedBody, requiresAuth: requiresAuth)
    }

    private func performRequest(
        _ path: String,
        method: HTTPMethod,
        body: Data?,
        requiresAuth: Bool,
        didRetryAfterUnauthorized: Bool
    ) async throws -> Data {
        let url = try makeURL(for: path)
        var request = URLRequest(url: url)
        request.httpMethod = method.rawValue
        request.setValue("application/json", forHTTPHeaderField: "Accept")

        if let body {
            request.httpBody = body
            request.setValue("application/json", forHTTPHeaderField: "Content-Type")
        }

        try attachAuthorization(to: &request, requiresAuth: requiresAuth)

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

        let bodyText = String(data: data, encoding: .utf8) ?? ""

        if httpResponse.statusCode == 401,
           requiresAuth,
           !didRetryAfterUnauthorized,
           let tokenRefresher {
            if let refreshedToken = try await tokenRefresher(), !refreshedToken.isEmpty {
                request.setValue("Bearer \(refreshedToken)", forHTTPHeaderField: "Authorization")
                return try await performRequest(
                    path,
                    method: method,
                    body: body,
                    requiresAuth: requiresAuth,
                    didRetryAfterUnauthorized: true
                )
            }

            if let onUnauthorized {
                await onUnauthorized()
            }
            throw APIError.unauthorized
        }

        guard (200 ... 299).contains(httpResponse.statusCode) else {
            throw APIError.fromResponse(status: httpResponse.statusCode, body: bodyText)
        }

        return data
    }

    private func makeURL(for path: String) throws -> URL {
        guard let url = URL(string: path, relativeTo: baseURL)?.absoluteURL else {
            throw APIError.transport(URLError(.badURL))
        }
        return url
    }

    private func attachAuthorization(to request: inout URLRequest, requiresAuth: Bool) throws {
        let token = tokenProvider?()

        if requiresAuth && (token == nil || token?.isEmpty == true) {
            throw APIError.unauthorized
        }

        if let token, !token.isEmpty {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
    }
}
