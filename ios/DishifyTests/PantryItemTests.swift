import XCTest
@testable import Dishify

final class PantryItemTests: XCTestCase {
    func testSerializesStructuredIngredientFromAPIExample() throws {
        let item = PantryItem(rawText: "penne", quantityText: "12", unit: "oz")
        let ingredient = try XCTUnwrap(item.toParsedIngredient())

        let data = try JSONEncoder().encode(ingredient)
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]

        XCTAssertEqual(json?["name"] as? String, "penne")
        XCTAssertEqual(json?["quantity"] as? Double, 12)
        XCTAssertEqual(json?["unit"] as? String, "oz")
        XCTAssertEqual(json?["raw_text"] as? String, "penne")
    }

    func testSerializesIngredientWithNullQuantityAndUnit() throws {
        let item = PantryItem(rawText: "tomato", quantityText: "", unit: "")
        let ingredient = try XCTUnwrap(item.toParsedIngredient())

        let data = try JSONEncoder().encode(ingredient)
        let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]

        XCTAssertEqual(json?["name"] as? String, "tomato")
        XCTAssertEqual(json?["raw_text"] as? String, "tomato")
        XCTAssertNil(json?["quantity"])
        XCTAssertNil(json?["unit"])
    }

    func testOmitsEmptyRowsWhenBuildingList() {
        let items = [
            PantryItem(rawText: "penne", quantityText: "12", unit: "oz"),
            PantryItem(rawText: "   ", quantityText: "", unit: ""),
            PantryItem(rawText: "tomato", quantityText: "", unit: ""),
        ]

        let ingredients = PantryItem.parsedIngredients(from: items)

        XCTAssertEqual(ingredients.count, 2)
        XCTAssertEqual(ingredients[0].name, "penne")
        XCTAssertEqual(ingredients[1].name, "tomato")
    }

    func testRoundTripsParsedIngredientFields() {
        let original = ParsedIngredient(
            name: "spinach",
            quantity: 2.5,
            unit: "cup",
            rawText: "spinach"
        )

        let restored = PantryItem(parsedIngredient: original).toParsedIngredient()

        XCTAssertEqual(restored, original)
    }

    func testDecodesAPIExamplePantryList() throws {
        let json = """
        [
          {
            "name": "penne",
            "quantity": 12,
            "unit": "oz",
            "raw_text": "12 oz penne"
          },
          {
            "name": "tomato",
            "quantity": null,
            "unit": null,
            "raw_text": "tomato"
          }
        ]
        """

        let decoded = try JSONDecoder().decode([ParsedIngredient].self, from: Data(json.utf8))
        let items = PantryItem.items(from: decoded)

        XCTAssertEqual(items.count, 2)
        XCTAssertEqual(items[0].rawText, "12 oz penne")
        XCTAssertEqual(items[0].quantityText, "12")
        XCTAssertEqual(items[0].unit, "oz")
        XCTAssertEqual(items[1].rawText, "tomato")
    }
}
