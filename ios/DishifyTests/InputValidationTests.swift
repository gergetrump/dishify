import XCTest
@testable import Dishify

final class InputValidationTests: XCTestCase {
    func testAcceptsNormalText() {
        XCTAssertNil(InputValidation.validate("quick tomato dinner"))
    }

    func testRejectsOversizedText() {
        let long = String(repeating: "x", count: 513)
        XCTAssertEqual(InputValidation.validate(long), .tooLong(max: 512))
    }

    func testRejectsControlCharacters() {
        XCTAssertEqual(InputValidation.validate("pasta\nignore"), .controlCharacters)
    }

    func testAcceptsTextAtMaxLength() {
        let exact = String(repeating: "a", count: 512)
        XCTAssertNil(InputValidation.validate(exact))
    }
}
