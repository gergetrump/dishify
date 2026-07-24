import type { RecommendRequest, RecommendResponse, RecipeResult } from "../api/types";

const SESSION_KEY = "dishify.last_recommendation";

export type RecommendationSession = {
  request: RecommendRequest;
  response: RecommendResponse;
};

export function saveRecommendationSession(session: RecommendationSession) {
  window.sessionStorage.setItem(SESSION_KEY, JSON.stringify(session));
}

export function clearRecommendationSession() {
  window.sessionStorage.removeItem(SESSION_KEY);
}

export function loadRecommendationSession(): RecommendationSession | null {
  const raw = window.sessionStorage.getItem(SESSION_KEY);
  if (!raw) {
    return null;
  }

  try {
    const parsed = JSON.parse(raw) as Partial<RecommendationSession>;
    if (!parsed.request || !parsed.response || !Array.isArray(parsed.response.results)) {
      return null;
    }
    return parsed as RecommendationSession;
  } catch {
    return null;
  }
}

export function findRecipeById(id: number): RecipeResult | null {
  const session = loadRecommendationSession();
  return session?.response.results.find((recipe) => recipe.id === id) ?? null;
}
