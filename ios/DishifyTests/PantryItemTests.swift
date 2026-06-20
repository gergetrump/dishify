import XCTest
@testable import Dishify

final class PantryItemTests: XCTestCase {
    func testPantryStoreCreatesRawText() {
        let item = PantryStore.make(name: "penne", quantity: 12, unit: "oz")

        XCTAssertEqual(item.name, "penne")
        XCTAssertEqual(item.quantity, 12)
        XCTAssertEqual(item.unit, "oz")
        XCTAssertEqual(item.rawText, "12 oz penne")
        XCTAssertNotNil(item.id)
    }

    func testPantryStoreCreatesRawTextWithoutQuantityOrUnit() {
        let item = PantryStore.make(name: "tomato", quantity: nil, unit: "")

        XCTAssertEqual(item.rawText, "tomato")
        XCTAssertNil(item.unit)
    }
}
