import { apiClient } from "../api/client";
import type { AugmentResponse, RecipeResult } from "../api/types";

// Per-session cache of recipe-direction enhancements, keyed by recipe id.
// We prefetch these as soon as recommendations arrive, so opening a recipe
// shows the enhanced steps instantly (no loading state).
const cache = new Map<number, Promise<AugmentResponse>>();

export function prefetchAugment(recipe: RecipeResult): Promise<AugmentResponse> {
  const existing = cache.get(recipe.id);
  if (existing) {
    return existing;
  }

  const promise = apiClient
    .augmentRecipe({
      title: recipe.title,
      ingredients: [...(recipe.inventory_matched ?? []), ...(recipe.inventory_missing ?? [])],
      directions: recipe.directions ?? [],
    })
    .catch((error) => {
      // Drop failures so a later open can retry.
      cache.delete(recipe.id);
      throw error;
    });

  cache.set(recipe.id, promise);
  return promise;
}

export function getAugment(recipeId: number): Promise<AugmentResponse> | undefined {
  return cache.get(recipeId);
}

export function prefetchAugmentAll(recipes: RecipeResult[]): void {
  for (const recipe of recipes) {
    // Swallow here; consumers attach their own handlers.
    void prefetchAugment(recipe).catch(() => {});
  }
}

export function clearAugmentCache(): void {
  cache.clear();
}
