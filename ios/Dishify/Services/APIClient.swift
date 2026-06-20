import Foundation

enum APIClientError: LocalizedError {
	case invalidURL
	case invalidResponse
	case serverError(Int)

	var errorDescription: String? {
		switch self {
		case .invalidURL:
			return "Invalid backend URL"
		case .invalidResponse:
			return "Invalid response from server"
		case .serverError(let code):
			return "Server error (\(code))"
		}
	}
}

@MainActor
final class APIClient: ObservableObject {
	static let shared = APIClient()

	/// Day 1: `true` for offline UI. Day 2+: `false` for real backend.
	var useMock = false

	var baseURL = URL(string: "http://127.0.0.1:8000")!
	var accessToken: String?

	func recommend(ingredients: [String], limit: Int = 5) async throws -> RecommendResponse {
		if useMock {
			return mockResponse(ingredients: ingredients, limit: limit)
		}
		return try await fetchRecommend(ingredients: ingredients, limit: limit)
	}

	private func fetchRecommend(ingredients: [String], limit: Int) async throws -> RecommendResponse {
		guard let url = URL(string: "/recommend", relativeTo: baseURL) else {
			throw APIClientError.invalidURL
		}

		var request = URLRequest(url: url)
		request.httpMethod = "POST"
		request.setValue("application/json", forHTTPHeaderField: "Content-Type")
		if let accessToken {
			request.setValue("Bearer \(accessToken)", forHTTPHeaderField: "Authorization")
		}

		let body = RecommendRequest(ingredients: ingredients, limit: limit)
		request.httpBody = try JSONEncoder().encode(body)

		let (data, response) = try await URLSession.shared.data(for: request)
		guard let http = response as? HTTPURLResponse else {
			throw APIClientError.invalidResponse
		}
		guard (200 ..< 300).contains(http.statusCode) else {
			throw APIClientError.serverError(http.statusCode)
		}

		return try JSONDecoder().decode(RecommendResponse.self, from: data)
	}

	private func mockResponse(ingredients: [String], limit: Int) -> RecommendResponse {
		let normalized = ingredients.map { $0.trimmingCharacters(in: .whitespacesAndNewlines).lowercased() }
		let items = [
			RecommendationItem(
				recipeId: "mock-1",
				title: "Caprese Pasta",
				score: 0.87,
				matchedIngredients: Array(normalized.prefix(2)),
				missingIngredients: ["basil"],
				reason: "Uses most of what you have."
			),
			RecommendationItem(
				recipeId: "mock-2",
				title: "Simple Tomato Pasta",
				score: 0.75,
				matchedIngredients: Array(normalized.prefix(1)),
				missingIngredients: ["garlic", "olive oil"],
				reason: "Quick pantry pasta with strong ingredient overlap."
			),
		]
		return RecommendResponse(
			recommendations: Array(items.prefix(limit)),
			stages: [
				PipelineStage(name: "normalize", status: "ok", latencyMs: 1),
				PipelineStage(name: "filter", status: "pending", latencyMs: 0),
			]
		)
	}
}
