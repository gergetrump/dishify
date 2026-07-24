import { beforeEach, describe, expect, it } from "vitest";

import {
  findRecipeById,
  loadRecommendationSession,
  saveRecommendationSession,
  type RecommendationSession,
} from "./session";

const session: RecommendationSession = {
  request: {
    query: "quick pasta",
    top_k: 2,
    available_ingredients: [
      {
        name: "penne",
        quantity: null,
        unit: null,
        raw_text: "penne",
      },
    ],
  },
  response: {
    results: [
      {
        rank: 1,
        id: 42,
        title: "Penne Dinner",
        score: 0.83,
        reasoning: {
          positive: ["Uses penne."],
          negative: ["Needs spinach."],
        },
        inventory_matched: ["penne"],
        inventory_missing: ["spinach"],
      },
    ],
  },
};

describe("recommendation session storage", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it("saves and loads the latest recommendation session", () => {
    saveRecommendationSession(session);

    expect(loadRecommendationSession()).toEqual(session);
  });

  it("returns null when stored data is malformed", () => {
    window.sessionStorage.setItem("dishify.last_recommendation", JSON.stringify({ nope: true }));

    expect(loadRecommendationSession()).toBeNull();
  });

  it("finds recipes from the latest stored response", () => {
    saveRecommendationSession(session);

    expect(findRecipeById(42)?.title).toBe("Penne Dinner");
    expect(findRecipeById(999)).toBeNull();
  });
});
