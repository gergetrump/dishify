import XCTest
@testable import Dishify

final class ConfigTests: XCTestCase {
    func testAPIBaseURLIsValidHTTPURL() {
        XCTAssertNotNil(Config.apiBaseURL.scheme)
        XCTAssertNotNil(Config.apiBaseURL.host)
    }

    func testAPIBaseURLUsesLocalDevelopmentGateway() {
        XCTAssertEqual(Config.apiBaseURL.scheme, "http")
        let host = Config.apiBaseURL.host ?? ""
        XCTAssertFalse(host.isEmpty)
        // Simulator/CI default (localhost), Bonjour host, or Debug.local LAN IP.
        let isLocalhost = host == "localhost"
        let isBonjour = host.hasSuffix(".local")
        let isPrivateLAN = host.hasPrefix("192.168.") || host.hasPrefix("10.") || host.hasPrefix("172.")
        XCTAssertTrue(isLocalhost || isBonjour || isPrivateLAN)
    }
}
