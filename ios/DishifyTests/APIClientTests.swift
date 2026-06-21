import XCTest
@testable import Dishify

final class APIClientTests: XCTestCase {
    override func tearDown() {
        MockURLProtocol.requestHandler = nil
        super.tearDown()
    }

    func testHealthDecodesSuccessResponse() async throws {
        let client = makeClient { request in
            XCTAssertEqual(request.url?.path, "/health")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Accept"), "application/json")
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 200,
                httpVersion: nil,
                headerFields: nil
            )!
            let body = """
            {"status":"ok","service":"dishify-backend"}
            """.data(using: .utf8)!
            return (response, body)
        }

        let health = try await client.health()

        XCTAssertEqual(health.status, "ok")
        XCTAssertEqual(health.service, "dishify-backend")
    }

    func testMaps401ToUnauthorized() async {
        let client = makeClient { request in
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 401,
                httpVersion: nil,
                headerFields: nil
            )!
            return (response, Data())
        }

        do {
            _ = try await client.health() as HealthResponse
            XCTFail("Expected unauthorized error")
        } catch let error as APIError {
            XCTAssertEqual(error.errorDescription, APIError.auth.errorDescription)
        } catch {
            XCTFail("Unexpected error: \(error)")
        }
    }

    func testMaps422ToValidation() async {
        let client = makeClient { request in
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 422,
                httpVersion: nil,
                headerFields: nil
            )!
            let body = """
            {"detail":"Unknown restriction tag"}
            """.data(using: .utf8)!
            return (response, body)
        }

        do {
            _ = try await client.health() as HealthResponse
            XCTFail("Expected validation error")
        } catch let error as APIError {
            if case .validation(let message) = error {
                XCTAssertEqual(message, "Unknown restriction tag")
            } else {
                XCTFail("Expected validation error, got \(error)")
            }
        } catch {
            XCTFail("Unexpected error: \(error)")
        }
    }

    func testMaps503ToServerUnavailable() async {
        let client = makeClient { request in
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 503,
                httpVersion: nil,
                headerFields: nil
            )!
            return (response, Data("Service unavailable".utf8))
        }

        do {
            _ = try await client.health() as HealthResponse
            XCTFail("Expected server unavailable error")
        } catch let error as APIError {
            if case .unavailable(let detail) = error {
                XCTAssertEqual(detail, "Service unavailable")
            } else {
                XCTFail("Expected unavailable error, got \(error)")
            }
        } catch {
            XCTFail("Unexpected error: \(error)")
        }
    }

    func testAttachesBearerTokenWhenProviderReturnsValue() async throws {
        let client = makeClient(tokenProvider: { "test-token" }) { request in
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer test-token")
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 200,
                httpVersion: nil,
                headerFields: nil
            )!
            let body = """
            {"exclusion_restrictions":["vegetarian"]}
            """.data(using: .utf8)!
            return (response, body)
        }

        _ = try await client.preferences()
    }

    func testMeUsesBearerToken() async throws {
        let client = makeClient(tokenProvider: { "test-token" }) { request in
            XCTAssertEqual(request.url?.path, "/me")
            XCTAssertEqual(request.value(forHTTPHeaderField: "Authorization"), "Bearer test-token")
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 200,
                httpVersion: nil,
                headerFields: nil
            )!
            let body = """
            {"id":"user-1","username":"test","email":"test@example.com","email_verified":true,"first_name":"test","last_name":"User"}
            """.data(using: .utf8)!
            return (response, body)
        }

        let profile = try await client.me()

        XCTAssertEqual(profile.username, "test")
    }

    func testRetriesWithRefreshedTokenOn401() async throws {
        var callCount = 0
        let client = makeClient(
            tokenProvider: { "old-token" },
            refreshTokenProvider: { "old-rt" },
            onTokenRefreshed: { _, _ in },
            handler: { request in
                callCount += 1
                if callCount == 1 {
                    // First call: 401
                    let response = HTTPURLResponse(url: request.url!, statusCode: 401, httpVersion: nil, headerFields: nil)!
                    return (response, Data())
                } else if request.url?.path == "/auth/refresh" {
                    // Refresh call
                    let response = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                    let body = """
                    {"access_token":"new-at","expires_in":300,"refresh_token":"new-rt","token_type":"Bearer"}
                    """.data(using: .utf8)!
                    return (response, body)
                } else {
                    // Retry with new token
                    let response = HTTPURLResponse(url: request.url!, statusCode: 200, httpVersion: nil, headerFields: nil)!
                    let body = """
                    {"id":"u1","username":"test","email":"t@e.com","email_verified":true,"first_name":"test","last_name":"User"}
                    """.data(using: .utf8)!
                    return (response, body)
                }
            }
        )

        let profile = try await client.me()
        XCTAssertEqual(profile.username, "test")
        XCTAssertEqual(callCount, 3)
    }

    func testCallsOnRefreshFailedWhenRefreshFails() async {
        var refreshFailed = false
        var callCount = 0
        let client = makeClient(
            tokenProvider: { "bad-token" },
            refreshTokenProvider: { "bad-rt" },
            onRefreshFailed: { refreshFailed = true },
            handler: { request in
                callCount += 1
                let response = HTTPURLResponse(url: request.url!, statusCode: 401, httpVersion: nil, headerFields: nil)!
                return (response, Data())
            }
        )

        do {
            _ = try await client.me() as UserProfile
            XCTFail("Expected auth error")
        } catch let error as APIError {
            XCTAssertEqual(error.errorDescription, APIError.auth.errorDescription)
        } catch {
            XCTFail("Unexpected error: \(error)")
        }
        XCTAssertTrue(refreshFailed)
    }

    func testCallsOnRefreshFailedWhenNoRefreshToken() async {
        var refreshFailed = false
        let client = makeClient(
            tokenProvider: { "bad-token" },
            refreshTokenProvider: { nil },
            onRefreshFailed: { refreshFailed = true },
            handler: { request in
                let response = HTTPURLResponse(url: request.url!, statusCode: 401, httpVersion: nil, headerFields: nil)!
                return (response, Data())
            }
        )

        do {
            _ = try await client.me() as UserProfile
            XCTFail("Expected auth error")
        } catch let error as APIError {
            XCTAssertEqual(error.errorDescription, APIError.auth.errorDescription)
        } catch {
            XCTFail("Unexpected error: \(error)")
        }
        XCTAssertTrue(refreshFailed)
    }

    private func makeClient(
        tokenProvider: (() -> String?)? = nil,
        refreshTokenProvider: (() -> String?)? = nil,
        onTokenRefreshed: ((String, String?) -> Void)? = nil,
        onRefreshFailed: (() -> Void)? = nil,
        handler: @escaping (URLRequest) throws -> (HTTPURLResponse, Data)
    ) -> APIClient {
        MockURLProtocol.requestHandler = handler
        var client = APIClient(
            baseURL: URL(string: "http://localhost:8000")!,
            tokenProvider: tokenProvider ?? { nil },
            refreshTokenProvider: refreshTokenProvider ?? { nil },
            session: makeSession()
        )
        client.onTokenRefreshed = onTokenRefreshed
        client.onRefreshFailed = onRefreshFailed
        return client
    }

    private func makeSession() -> URLSession {
        let configuration = URLSessionConfiguration.ephemeral
        configuration.protocolClasses = [MockURLProtocol.self]
        return URLSession(configuration: configuration)
    }
}

private final class MockURLProtocol: URLProtocol {
    static var requestHandler: ((URLRequest) throws -> (HTTPURLResponse, Data))?

    override class func canInit(with request: URLRequest) -> Bool {
        true
    }

    override class func canonicalRequest(for request: URLRequest) -> URLRequest {
        request
    }

    override func startLoading() {
        guard let handler = Self.requestHandler else {
            client?.urlProtocol(self, didFailWithError: URLError(.badServerResponse))
            return
        }

        do {
            let (response, data) = try handler(request)
            client?.urlProtocol(self, didReceive: response, cacheStoragePolicy: .notAllowed)
            client?.urlProtocol(self, didLoad: data)
            client?.urlProtocolDidFinishLoading(self)
        } catch {
            client?.urlProtocol(self, didFailWithError: error)
        }
    }

    override func stopLoading() {}
}
