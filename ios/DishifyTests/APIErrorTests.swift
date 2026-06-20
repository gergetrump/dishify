import XCTest
@testable import Dishify

final class APIErrorTests: XCTestCase {
    func testAuthDescription() {
        XCTAssertEqual(
            APIError.auth.errorDescription,
            "Your session is missing or expired. Log in again."
        )
    }

    func testUnavailableDescriptionFallsBackWhenDetailMissing() {
        XCTAssertEqual(
            APIError.unavailable(nil).errorDescription,
            "Dishify is not ready yet. Check backend services and indexing."
        )
    }

    func testUnavailableDescriptionUsesDetailWhenPresent() {
        XCTAssertEqual(
            APIError.unavailable("Recipes are not indexed yet.").errorDescription,
            "Recipes are not indexed yet."
        )
    }

    func testValidationDescriptionPassesThroughMessage() {
        XCTAssertEqual(APIError.validation("Unknown restriction tag").errorDescription, "Unknown restriction tag")
    }

    func testUserMessageUsesContextForServerUnavailable() {
        XCTAssertEqual(
            APIError.unavailable(nil).userMessage(for: .recommend),
            "The recommendation service is warming up. Make sure the backend is running and recipes are indexed."
        )
        XCTAssertEqual(
            APIError.unavailable(nil).userMessage(for: .preferences),
            "Preferences service is temporarily unavailable. Try again shortly."
        )
        XCTAssertEqual(
            APIError.unavailable(nil).userMessage(for: .general),
            "Service temporarily unavailable."
        )
    }

    func testUserMessageAppendsServerDetailWhenPresent() {
        let error = APIError.unavailable("Recipes are not indexed yet.")
        let message = error.userMessage(for: .recommend)
        XCTAssertTrue(
            message.contains("The recommendation service is warming up."),
            "Expected fallback copy, got \(message)"
        )
        XCTAssertTrue(
            message.contains("Recipes are not indexed yet."),
            "Expected backend detail to be appended, got \(message)"
        )
    }

    func testUserMessagePassesThroughValidationMessage() {
        let error = APIError.validation("Unknown restriction tag")
        XCTAssertEqual(error.userMessage(for: .preferences), "Unknown restriction tag")
    }

    func testUserMessageForUnauthorized() {
        XCTAssertEqual(
            APIError.auth.userMessage(for: .general),
            "Your session expired. Sign in again."
        )
    }
}
