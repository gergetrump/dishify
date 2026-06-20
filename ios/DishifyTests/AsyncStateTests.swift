import XCTest
@testable import Dishify

final class AsyncStateTests: XCTestCase {
    func testIdleStateProperties() {
        let state: AsyncState<String> = .idle

        XCTAssertFalse(state.isLoading)
        XCTAssertNil(state.value)
        XCTAssertNil(state.errorMessage)
    }

    func testLoadingStateProperties() {
        let state: AsyncState<String> = .loading

        XCTAssertTrue(state.isLoading)
        XCTAssertNil(state.value)
        XCTAssertNil(state.errorMessage)
    }

    func testLoadedStateProperties() {
        let state: AsyncState<String> = .loaded("recipes")

        XCTAssertFalse(state.isLoading)
        XCTAssertEqual(state.value, "recipes")
        XCTAssertNil(state.errorMessage)
    }

    func testFailedStateProperties() {
        let state: AsyncState<String> = .failed("Something went wrong")

        XCTAssertFalse(state.isLoading)
        XCTAssertNil(state.value)
        XCTAssertEqual(state.errorMessage, "Something went wrong")
    }

    func testLoadMarkerEquatable() {
        XCTAssertEqual(LoadMarker.ready, LoadMarker.ready)
    }
}
