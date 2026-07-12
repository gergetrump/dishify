import XCTest
@testable import Dishify

final class PantryItemTests: XCTestCase {
    func testPantryStoreCreatesRawText() {
        let item = PantryStore.make(name: "penne", quantity: 12, unit: "oz")

        XCTAssertEqual(item.name, "Penne")
        XCTAssertEqual(item.quantity, 12)
        XCTAssertEqual(item.unit, "oz")
        XCTAssertEqual(item.rawText, "12 oz Penne")
        XCTAssertNotNil(item.id)
    }

    func testPantryStoreCreatesRawTextWithoutQuantityOrUnit() {
        let item = PantryStore.make(name: "tomato", quantity: nil, unit: "")

        XCTAssertEqual(item.name, "Tomato")
        XCTAssertEqual(item.rawText, "Tomato")
        XCTAssertNil(item.unit)
    }

    func testIngredientFormattingCapitalizesDisplayName() {
        XCTAssertEqual(IngredientFormatting.displayName("extra virgin olive oil"), "Extra virgin olive oil")
        XCTAssertEqual(IngredientFormatting.displayName("  garlic  "), "Garlic")
    }
}
