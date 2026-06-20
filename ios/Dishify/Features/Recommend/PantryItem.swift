import Foundation

enum PantryStore {
    private static let key = "dishify.pantry"

    static func load() -> [ParsedIngredient] {
        guard let data = UserDefaults.standard.data(forKey: key),
              let items = try? JSONDecoder().decode([ParsedIngredient].self, from: data) else {
            return []
        }
        return items.filter { !$0.name.isEmpty }
    }

    static func save(_ items: [ParsedIngredient]) {
        guard let data = try? JSONEncoder().encode(items) else { return }
        UserDefaults.standard.set(data, forKey: key)
    }

    static func make(name: String, quantity: Double?, unit: String?) -> ParsedIngredient {
        let trimmedName = name.trimmingCharacters(in: .whitespacesAndNewlines)
        let normalizedUnit = unit?.trimmingCharacters(in: .whitespacesAndNewlines)
        let amount = quantity.map { String(format: "%g", $0) } ?? ""
        let rawText = [amount, normalizedUnit ?? "", trimmedName]
            .filter { !$0.isEmpty }
            .joined(separator: " ")
        return ParsedIngredient(
            id: UUID().uuidString,
            name: trimmedName,
            quantity: quantity,
            unit: normalizedUnit?.isEmpty == true ? nil : normalizedUnit,
            rawText: rawText
        )
    }
}

enum RecommendationStore {
    private static let key = "dishify.last_recommendation"

    static func load() -> RecommendationSession? {
        guard let data = UserDefaults.standard.data(forKey: key) else { return nil }
        return try? JSONDecoder().decode(RecommendationSession.self, from: data)
    }

    static func save(_ session: RecommendationSession) {
        guard let data = try? JSONEncoder().encode(session) else { return }
        UserDefaults.standard.set(data, forKey: key)
    }

    static func findRecipe(id: Int) -> RecipeResult? {
        load()?.response.results.first { $0.id == id }
    }
}
