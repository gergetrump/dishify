import Foundation

struct RecommendRequest: Encodable {
	let ingredients: [String]
	let limit: Int
}

struct RecommendResponse: Decodable {
	let recommendations: [RecommendationItem]
	let stages: [PipelineStage]
}

struct RecommendationItem: Decodable, Identifiable {
	var id: String { recipeId }
	let recipeId: String
	let title: String
	let score: Double
	let matchedIngredients: [String]
	let missingIngredients: [String]
	let reason: String

	enum CodingKeys: String, CodingKey {
		case recipeId = "recipe_id"
		case title
		case score
		case matchedIngredients = "matched_ingredients"
		case missingIngredients = "missing_ingredients"
		case reason
	}
}

struct PipelineStage: Decodable {
	let name: String
	let status: String
	let latencyMs: Int

	enum CodingKeys: String, CodingKey {
		case name
		case status
		case latencyMs = "latency_ms"
	}
}
