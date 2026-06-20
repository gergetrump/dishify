import XCTest
@testable import Dishify

final class RecipeResultFormattingTests: XCTestCase {
    func testMatchLabelFormatsPercentage() {
        XCTAssertEqual(RecipeResultFormatting.matchLabel(for: 0.59), "59% match")
        XCTAssertEqual(RecipeResultFormatting.matchLabel(for: 0), "0% match")
        XCTAssertEqual(RecipeResultFormatting.matchLabel(for: 1), "100% match")
    }

    func testDurationLabelUsesSingularMinute() {
        XCTAssertEqual(RecipeResultFormatting.durationLabel(for: 1), "1 minute")
    }

    func testDurationLabelUsesPluralMinutes() {
        XCTAssertEqual(RecipeResultFormatting.durationLabel(for: 45), "45 minutes")
    }
}
