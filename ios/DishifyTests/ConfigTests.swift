import XCTest
@testable import Dishify

final class ConfigTests: XCTestCase {
    func testRedirectURIUsesDishifyScheme() {
        XCTAssertEqual(Config.redirectURI, "dishify://callback")
    }

    func testIOSClientIDMatchesKeycloakClient() {
        XCTAssertEqual(Config.iosClientID, "dishify-ios")
    }

    func testRealmMatchesBackendContract() {
        XCTAssertEqual(Config.realm, "dishify")
    }

    func testAPIBaseURLIsValidHTTPURL() {
        XCTAssertNotNil(Config.apiBaseURL.scheme)
        XCTAssertNotNil(Config.apiBaseURL.host)
    }

    func testBuildFlavorIsNonEmpty() {
        XCTAssertFalse(Config.buildFlavor.isEmpty)
    }
}
