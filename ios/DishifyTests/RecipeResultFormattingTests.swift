import XCTest
@testable import Dishify

final class RecipeResultFormattingTests: XCTestCase {
    func testRecipeResultDecodesWebShape() throws {
        let json = """
        {
          "rank": 1,
          "id": 3136,
          "title": "Pasta With Spinach Sauce",
          "summary": null,
          "time_minutes": 30,
          "score": 0.87,
          "reasoning": {
            "positive": ["Uses spinach from your pantry."],
            "negative": ["You may need cream."]
          },
          "directions": ["Cook pasta.", "Blend spinach sauce."],
          "inventory_matched": ["spinach", "pasta"],
          "inventory_missing": ["cream"]
        }
        """

        let recipe = try JSONDecoder().decode(RecipeResult.self, from: Data(json.utf8))

        XCTAssertEqual(recipe.id, 3136)
        XCTAssertEqual(recipe.timeMinutes, 30)
        XCTAssertEqual(recipe.inventoryMatched, ["spinach", "pasta"])
        XCTAssertEqual(recipe.reasoning?.positive.first, "Uses spinach from your pantry.")
    }
}
