import Foundation

enum IngredientFormatting {
    static func displayName(_ value: String) -> String {
        let trimmed = value.trimmingCharacters(in: .whitespacesAndNewlines)
        guard let first = trimmed.first else { return trimmed }
        return String(first).uppercased() + trimmed.dropFirst()
    }
}

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
        let trimmedName = IngredientFormatting.displayName(name)
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

enum VibeDraftStore {
    private static let key = "dishify.pending_vibe_query"

    static func load() -> String {
        UserDefaults.standard.string(forKey: key) ?? ""
    }

    static func save(_ query: String) {
        let trimmed = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        UserDefaults.standard.set(trimmed, forKey: key)
    }

    static func clear() {
        UserDefaults.standard.removeObject(forKey: key)
    }
}
