import XCTest
@testable import Dishify

final class ModelDecodingTests: XCTestCase {
    private let decoder = JSONDecoder()

    func testDecodesHealthResponse() throws {
        let json = """
        {
          "status": "ok",
          "service": "dishify-backend"
        }
        """

        let response = try decoder.decode(HealthResponse.self, from: Data(json.utf8))

        XCTAssertEqual(response.status, "ok")
        XCTAssertEqual(response.service, "dishify-backend")
    }

    func testDecodesTokenResponse() throws {
        let json = """
        {
          "access_token": "<jwt>",
          "expires_in": 300,
          "refresh_token": "<refresh_token>",
          "token_type": "Bearer",
          "scope": "openid profile email"
        }
        """

        let token = try decoder.decode(TokenResponse.self, from: Data(json.utf8))

        XCTAssertEqual(token.accessToken, "<jwt>")
        XCTAssertEqual(token.expiresIn, 300)
        XCTAssertEqual(token.refreshToken, "<refresh_token>")
        XCTAssertEqual(token.tokenType, "Bearer")
        XCTAssertEqual(token.scope, "openid profile email")
    }

    func testDecodesRegisterResponse() throws {
        let json = """
        {
          "id": "4267aa58-4ec7-4f83-a8eb-ada7b8743d88",
          "username": "demo_user",
          "email": "demo@example.com",
          "message": "Registration successful"
        }
        """

        let response = try decoder.decode(RegisterResponse.self, from: Data(json.utf8))

        XCTAssertEqual(response.id, "4267aa58-4ec7-4f83-a8eb-ada7b8743d88")
        XCTAssertEqual(response.username, "demo_user")
        XCTAssertEqual(response.message, "Registration successful")
    }

    func testDecodesUserProfile() throws {
        let json = """
        {
          "id": "4267aa58-4ec7-4f83-a8eb-ada7b8743d88",
          "username": "demo_user",
          "email": "demo@example.com",
          "email_verified": true,
          "first_name": "demo_user",
          "last_name": "User"
        }
        """

        let profile = try decoder.decode(UserProfile.self, from: Data(json.utf8))

        XCTAssertEqual(profile.username, "demo_user")
        XCTAssertEqual(profile.emailVerified, true)
        XCTAssertEqual(profile.lastName, "User")
    }

    func testDecodesUserProfileWithNullNames() throws {
        let json = """
        {
          "id": "25f4a8eb-ac4e-42a0-be47-e8a9c65b0b17",
          "username": "testuser",
          "email": "test@dishify.com",
          "email_verified": true,
          "first_name": null,
          "last_name": null
        }
        """

        let profile = try decoder.decode(UserProfile.self, from: Data(json.utf8))

        XCTAssertEqual(profile.username, "testuser")
        XCTAssertNil(profile.firstName)
        XCTAssertNil(profile.lastName)
    }

    func testDecodesUserPreferences() throws {
        let json = """
        {
          "exclusion_restrictions": ["shellfish_allergy", "nut_allergy", "vegetarian"]
        }
        """

        let preferences = try decoder.decode(UserPreferences.self, from: Data(json.utf8))

        XCTAssertEqual(
            preferences.exclusionRestrictions,
            ["shellfish_allergy", "nut_allergy", "vegetarian"]
        )
    }

    func testDecodesRecommendResponse() throws {
        let json = """
        {
          "results": [
            {
              "rank": 1,
              "id": 3136,
              "title": "Pasta With Spinach Sauce",
              "summary": null,
              "time_minutes": null,
              "score": 0.59,
              "reasoning": {
                "positive": ["Uses penne and spinach from your pantry."],
                "negative": ["Requires bacon and whipping cream."]
              },
              "directions": ["Cook pasta as directed.", "..."],
              "inventory_matched": ["penne", "spinach"],
              "inventory_missing": ["bacon", "whipping cream"]
            }
          ],
          "stages": [
            {"name": "retrieve", "status": "ok", "latency_ms": 120},
            {"name": "rank", "status": "ok", "latency_ms": 2},
            {"name": "explain", "status": "skipped", "latency_ms": 0}
          ]
        }
        """

        let response = try decoder.decode(RecommendResponse.self, from: Data(json.utf8))

        XCTAssertEqual(response.results.count, 1)
        XCTAssertEqual(response.results[0].id, 3136)
        XCTAssertNil(response.results[0].summary)
        XCTAssertNil(response.results[0].timeMinutes)
        XCTAssertEqual(response.results[0].reasoning?.positive.first, "Uses penne and spinach from your pantry.")
        XCTAssertEqual(response.stages.map(\.name), ["retrieve", "rank", "explain"])
        XCTAssertEqual(response.stages[2].status, "skipped")
    }

    func testDecodesRecommendRequestWithPantry() throws {
        let json = """
        {
          "query": "creamy tomato pasta with spinach",
          "top_k": 5,
          "available_ingredients": [
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
        }
        """

        let request = try decoder.decode(RecommendRequest.self, from: Data(json.utf8))

        XCTAssertEqual(request.query, "creamy tomato pasta with spinach")
        XCTAssertEqual(request.topK, 5)
        XCTAssertEqual(request.availableIngredients?.count, 2)
        XCTAssertEqual(request.availableIngredients?[0].name, "penne")
        XCTAssertEqual(request.availableIngredients?[0].quantity, 12)
        XCTAssertEqual(request.availableIngredients?[1].quantity, nil)
        XCTAssertNil(request.exclusionRestrictions)
    }

    func testEncodesRecommendRequestRoundTrip() throws {
        let request = RecommendRequest(
            query: "creamy tomato pasta with spinach",
            topK: 5,
            availableIngredients: [
                ParsedIngredient(name: "penne", quantity: 12, unit: "oz", rawText: "12 oz penne"),
                ParsedIngredient(name: "tomato", quantity: nil, unit: nil, rawText: "tomato"),
            ],
            exclusionRestrictions: nil
        )

        let data = try JSONEncoder().encode(request)
        let decoded = try decoder.decode(RecommendRequest.self, from: data)

        XCTAssertEqual(decoded, request)
    }

    func testEncodesRecommendRequestWithRestrictionsOverride() throws {
        let request = RecommendRequest(
            query: "creamy tomato pasta with spinach",
            topK: 5,
            availableIngredients: nil,
            exclusionRestrictions: ["shellfish_allergy", "nut_allergy", "vegetarian"]
        )

        let data = try JSONEncoder().encode(request)
        let decoded = try decoder.decode(RecommendRequest.self, from: data)

        XCTAssertEqual(decoded.exclusionRestrictions, ["shellfish_allergy", "nut_allergy", "vegetarian"])
        XCTAssertNil(decoded.availableIngredients)
    }

    func testEncodesRegisterRequestFromAPIExample() throws {
        let request = RegisterRequest(
            username: "demo_user",
            email: "demo@example.com",
            password: "demo-secret-1",
            exclusionRestrictions: ["shellfish_allergy", "nut_allergy"]
        )

        let data = try JSONEncoder().encode(request)
        let object = try JSONSerialization.jsonObject(with: data) as? [String: Any]

        XCTAssertEqual(object?["username"] as? String, "demo_user")
        XCTAssertEqual(object?["email"] as? String, "demo@example.com")
        XCTAssertEqual(object?["password"] as? String, "demo-secret-1")
        XCTAssertEqual(
            object?["exclusion_restrictions"] as? [String],
            ["shellfish_allergy", "nut_allergy"]
        )
    }

    func testEncodesLoginRequestFromAPIExample() throws {
        let request = LoginRequest(username: "demo_user", password: "demo-secret-1")

        let data = try JSONEncoder().encode(request)
        let object = try JSONSerialization.jsonObject(with: data) as? [String: Any]

        XCTAssertEqual(object?["username"] as? String, "demo_user")
        XCTAssertEqual(object?["password"] as? String, "demo-secret-1")
    }

    func testEncodesPreferencesUpdateRequestFromAPIExample() throws {
        let request = UpdatePreferencesRequest(
            exclusionRestrictions: ["shellfish_allergy", "nut_allergy", "vegetarian"]
        )

        let data = try JSONEncoder().encode(request)
        let decoded = try decoder.decode(UserPreferences.self, from: data)

        XCTAssertEqual(
            decoded.exclusionRestrictions,
            ["shellfish_allergy", "nut_allergy", "vegetarian"]
        )
    }

    func testDecodesRecipeResultWithOptionalFieldsPopulated() throws {
        let json = """
        {
          "rank": 2,
          "id": 42,
          "title": "Quick Tomato Soup",
          "summary": "A fast weeknight soup.",
          "time_minutes": 20,
          "score": 0.82,
          "reasoning": null,
          "directions": ["Simmer tomatoes."],
          "inventory_matched": ["tomato"],
          "inventory_missing": []
        }
        """

        let result = try decoder.decode(RecipeResult.self, from: Data(json.utf8))

        XCTAssertEqual(result.summary, "A fast weeknight soup.")
        XCTAssertEqual(result.timeMinutes, 20)
        XCTAssertNil(result.reasoning)
    }
}
