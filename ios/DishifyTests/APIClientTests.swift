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
            XCTAssertEqual(error.errorDescription, APIError.unauthorized.errorDescription)
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
            if case .serverUnavailable(let detail) = error {
                XCTAssertEqual(detail, "Service unavailable")
            } else {
                XCTFail("Expected serverUnavailable error, got \(error)")
            }
        } catch {
            XCTFail("Unexpected error: \(error)")
        }
    }

    func testRequiresAuthWhenTokenMissing() async {
        let client = APIClient(
            baseURL: URL(string: "http://localhost:8000")!,
            session: makeSession(),
            tokenProvider: { nil }
        )

        do {
            let _: UserProfile = try await client.request("/me", requiresAuth: true)
            XCTFail("Expected unauthorized error")
        } catch let error as APIError {
            XCTAssertEqual(error.errorDescription, APIError.unauthorized.errorDescription)
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
            {"status":"ok","service":"dishify-backend"}
            """.data(using: .utf8)!
            return (response, body)
        }

        _ = try await client.health()
    }

    func testRetriesOnceAfter401WhenTokenRefreshSucceeds() async throws {
        var apiRequestCount = 0
        var refreshCallCount = 0
        var unauthorizedHandled = false
        var currentToken = "stale-token"

        let client = makeClient(
            tokenProvider: { currentToken },
            tokenRefresher: {
                refreshCallCount += 1
                currentToken = "fresh-token"
                return currentToken
            },
            onUnauthorized: {
                unauthorizedHandled = true
            }
        ) { request in
            apiRequestCount += 1
            let statusCode = request.value(forHTTPHeaderField: "Authorization") == "Bearer stale-token" ? 401 : 200
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: statusCode,
                httpVersion: nil,
                headerFields: nil
            )!
            let body = """
            {"id":"user-1","username":"test","email":"test@example.com","email_verified":true,"first_name":"test","last_name":"User"}
            """.data(using: .utf8)!
            return (response, body)
        }

        let profile: UserProfile = try await client.request("/me", requiresAuth: true)

        XCTAssertEqual(profile.username, "test")
        XCTAssertEqual(apiRequestCount, 2)
        XCTAssertEqual(refreshCallCount, 1)
        XCTAssertFalse(unauthorizedHandled)
    }

    func testSignsOutWhenTokenRefreshFailsAfter401() async {
        var unauthorizedHandled = false

        let client = makeClient(
            tokenProvider: { "stale-token" },
            tokenRefresher: { nil },
            onUnauthorized: { unauthorizedHandled = true }
        ) { request in
            let response = HTTPURLResponse(
                url: request.url!,
                statusCode: 401,
                httpVersion: nil,
                headerFields: nil
            )!
            return (response, Data())
        }

        do {
            let _: UserProfile = try await client.request("/me", requiresAuth: true)
            XCTFail("Expected unauthorized error")
        } catch let error as APIError {
            XCTAssertEqual(error.errorDescription, APIError.unauthorized.errorDescription)
            XCTAssertTrue(unauthorizedHandled)
        } catch {
            XCTFail("Unexpected error: \(error)")
        }
    }

    private func makeClient(
        tokenProvider: AccessTokenProvider? = nil,
        tokenRefresher: AccessTokenRefresher? = nil,
        onUnauthorized: UnauthorizedHandler? = nil,
        handler: @escaping (URLRequest) throws -> (HTTPURLResponse, Data)
    ) -> APIClient {
        MockURLProtocol.requestHandler = handler
        return APIClient(
            baseURL: URL(string: "http://localhost:8000")!,
            session: makeSession(),
            tokenProvider: tokenProvider,
            tokenRefresher: tokenRefresher,
            onUnauthorized: onUnauthorized
        )
    }

    private func makeClient(
        tokenProvider: AccessTokenProvider? = nil,
        handler: @escaping (URLRequest) throws -> (HTTPURLResponse, Data)
    ) -> APIClient {
        makeClient(
            tokenProvider: tokenProvider,
            tokenRefresher: nil,
            onUnauthorized: nil,
            handler: handler
        )
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
