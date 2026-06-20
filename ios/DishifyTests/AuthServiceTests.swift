import XCTest
@testable import Dishify

final class AuthServiceTests: XCTestCase {
    func testAccessTokenStoreRoundTrip() {
        AccessTokenStore.clear()
        XCTAssertNil(AccessTokenStore.load())

        AccessTokenStore.save("access-token")
        XCTAssertEqual(AccessTokenStore.load(), "access-token")

        AccessTokenStore.clear()
        XCTAssertNil(AccessTokenStore.load())
    }
}
