import XCTest
@testable import Dishify

final class ConfigTests: XCTestCase {
    func testAPIBaseURLIsValidHTTPURL() {
        XCTAssertNotNil(Config.apiBaseURL.scheme)
        XCTAssertNotNil(Config.apiBaseURL.host)
    }

    func testDefaultAPIBaseURLMatchesWebClientDefault() {
        XCTAssertEqual(Config.apiBaseURL.absoluteString, "http://localhost:8000")
    }
}
