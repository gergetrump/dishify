import XCTest
@testable import Dishify

final class APIErrorTests: XCTestCase {
    func testFromResponseMaps401ToUnauthorized() {
        let error = APIError.fromResponse(status: 401, body: "")
        XCTAssertEqual(error.errorDescription, APIError.unauthorized.errorDescription)
    }

    func testFromResponseMaps503ToServerUnavailable() {
        let error = APIError.fromResponse(status: 503, body: "")
        if case .serverUnavailable(let detail) = error {
            XCTAssertNil(detail)
        } else {
            XCTFail("Expected serverUnavailable error, got \(error)")
        }
    }

    func testFromResponse503PreservesDetailFromJSONBody() {
        let error = APIError.fromResponse(
            status: 503,
            body: """
            {"detail":"Qdrant collection 'recipes_10000' not found. Run: docker compose run --rm indexing-worker --recreate"}
            """
        )

        if case .serverUnavailable(let detail) = error {
            XCTAssertEqual(
                detail,
                "Qdrant collection 'recipes_10000' not found. Run: docker compose run --rm indexing-worker --recreate"
            )
        } else {
            XCTFail("Expected serverUnavailable error, got \(error)")
        }
    }

    func testFromResponseMaps422WithDetailString() {
        let error = APIError.fromResponse(
            status: 422,
            body: """
            {"detail":"Unknown restriction tag"}
            """
        )

        if case .validation(let message) = error {
            XCTAssertEqual(message, "Unknown restriction tag")
        } else {
            XCTFail("Expected validation error, got \(error)")
        }
    }

    func testFromResponseMaps422WithMessageField() {
        let error = APIError.fromResponse(
            status: 422,
            body: """
            {"message":"Invalid request payload"}
            """
        )

        if case .validation(let message) = error {
            XCTAssertEqual(message, "Invalid request payload")
        } else {
            XCTFail("Expected validation error, got \(error)")
        }
    }

    func testFromResponseMaps422WithPydanticDetailArray() {
        let error = APIError.fromResponse(
            status: 422,
            body: """
            {"detail":[{"msg":"Field required"}]}
            """
        )

        if case .validation(let message) = error {
            XCTAssertEqual(message, "Field required")
        } else {
            XCTFail("Expected validation error, got \(error)")
        }
    }

    func testFromResponseMaps422WithEmptyBody() {
        let error = APIError.fromResponse(status: 422, body: "")

        if case .validation(let message) = error {
            XCTAssertEqual(message, "Validation failed.")
        } else {
            XCTFail("Expected validation error, got \(error)")
        }
    }

    func testFromResponseMapsUnknownStatusToHTTP() {
        let error = APIError.fromResponse(status: 409, body: "Conflict")

        if case .http(let status, let body) = error {
            XCTAssertEqual(status, 409)
            XCTAssertEqual(body, "Conflict")
        } else {
            XCTFail("Expected http error, got \(error)")
        }
    }

    func testUserMessageUsesContextForServerUnavailable() {
        XCTAssertEqual(
            APIError.serverUnavailable().userMessage(for: .recommend),
            "The recommendation service is warming up. Make sure the backend is running and recipes are indexed."
        )
        XCTAssertEqual(
            APIError.serverUnavailable().userMessage(for: .preferences),
            "Preferences service is temporarily unavailable. Try again shortly."
        )
        XCTAssertEqual(
            APIError.serverUnavailable().userMessage(for: .general),
            "Service temporarily unavailable."
        )
    }

    func testUserMessageAppendsServerDetailWhenPresent() {
        let error = APIError.serverUnavailable(detail: "Recipes are not indexed yet.")
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
            APIError.unauthorized.userMessage(for: .general),
            "Your session expired. Sign in again."
        )
    }
}
