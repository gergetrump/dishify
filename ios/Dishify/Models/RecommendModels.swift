import Foundation

struct ParsedIngredient: Codable, Equatable, Identifiable {
    var id: String?
    let name: String
    let quantity: Double?
    let unit: String?
    let rawText: String

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case quantity
        case unit
        case rawText = "raw_text"
    }
}

struct RecommendRequest: Codable, Equatable {
    let query: String
    let topK: Int?
    let availableIngredients: [ParsedIngredient]?
    let exclusionRestrictions: [String]?

    enum CodingKeys: String, CodingKey {
        case query
        case topK = "top_k"
        case availableIngredients = "available_ingredients"
        case exclusionRestrictions = "exclusion_restrictions"
    }
}

struct ReasoningDetail: Codable, Equatable {
    let positive: [String]
    let negative: [String]
}

struct RecipeResult: Codable, Equatable, Identifiable {
    let rank: Int
    let id: Int
    let title: String?
    let summary: String?
    let timeMinutes: Int?
    let score: Double
    let reasoning: ReasoningDetail?
    let directions: [String]?
    let inventoryMatched: [String]?
    let inventoryMissing: [String]?

    enum CodingKeys: String, CodingKey {
        case rank
        case id
        case title
        case summary
        case timeMinutes = "time_minutes"
        case score
        case reasoning
        case directions
        case inventoryMatched = "inventory_matched"
        case inventoryMissing = "inventory_missing"
    }
}

struct PipelineStage: Codable, Equatable, Identifiable {
    var id: String { name }
    let name: String
    let status: String
    let latencyMs: Int

    enum CodingKeys: String, CodingKey {
        case name
        case status
        case latencyMs = "latency_ms"
    }
}

struct RecommendResponse: Codable, Equatable {
    let results: [RecipeResult]
    let stages: [PipelineStage]
}

struct RecommendationSession: Codable, Equatable {
    let request: RecommendRequest
    let response: RecommendResponse
}
