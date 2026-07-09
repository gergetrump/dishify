import Foundation

enum AugmentCache {
    private static var cache: [Int: Task<AugmentResponse, Error>] = [:]

    static func prefetchAll(_ recipes: [RecipeResult], api: APIClient = APIClient()) {
        for recipe in recipes {
            prefetch(recipe, api: api)
        }
    }

    @discardableResult
    static func prefetch(_ recipe: RecipeResult, api: APIClient = APIClient()) -> Task<AugmentResponse, Error>? {
        if let existing = cache[recipe.id] {
            return existing
        }

        let request = augmentRequest(for: recipe)
        let task = Task {
            try await api.augmentRecipe(request)
        }
        cache[recipe.id] = task
        return task
    }

    static func get(recipeId: Int) -> Task<AugmentResponse, Error>? {
        cache[recipeId]
    }

    static func remove(recipeId: Int) {
        cache.removeValue(forKey: recipeId)
    }

    static func clear() {
        cache.removeAll()
    }

    private static func augmentRequest(for recipe: RecipeResult) -> AugmentRequest {
        AugmentRequest(
            title: recipe.title,
            ingredients: (recipe.inventoryMatched ?? []) + (recipe.inventoryMissing ?? []),
            directions: recipe.directions ?? []
        )
    }
}
