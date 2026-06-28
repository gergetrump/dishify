import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { act } from "react";
import { createRoot } from "react-dom/client";

import { RecipeDetailPage } from "./RecipeDetailPage";
import { apiClient } from "../api/client";
import { clearAugmentCache } from "../recommendations/augmentCache";
import type { RecipeResult } from "../api/types";

const recipe: RecipeResult = {
  rank: 1,
  id: 3136,
  title: "Pasta With Spinach Sauce",
  score: 0.87,
  reasoning: {
    positive: ["Uses spinach from your pantry."],
    negative: ["You may need cream."],
  },
  directions: ["Cook pasta.", "Blend spinach sauce."],
  inventory_matched: ["spinach", "pasta"],
  inventory_missing: ["cream"],
};

beforeEach(() => {
  clearAugmentCache();
});

afterEach(() => {
  vi.restoreAllMocks();
});

describe("RecipeDetailPage", () => {
  it("renders recipe details and auto-enhanced directions", async () => {
    vi.spyOn(apiClient, "augmentRecipe").mockResolvedValue({
      steps: [{ text: "Boil the pasta until al dente.", tip: null, duration_minutes: 10 }],
      tips: [],
      estimated_time_minutes: 20,
      latency_ms: 1,
    });

    const container = document.createElement("div");
    const root = createRoot(container);

    await act(async () => {
      root.render(
        <MemoryRouter
          future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
          initialEntries={[{ pathname: "/recipes/3136", state: { recipe } }]}
        >
          <Routes>
            <Route path="/recipes/:id" element={<RecipeDetailPage />} />
          </Routes>
        </MemoryRouter>,
      );
    });
    // flush the auto-enhance effect's resolved promise
    await act(async () => {});

    expect(apiClient.augmentRecipe).toHaveBeenCalled();
    expect(container.textContent).toContain("Pasta With Spinach Sauce");
    expect(container.textContent).toContain("Score 87");
    expect(container.textContent).toContain("Uses spinach from your pantry.");
    expect(container.textContent).toContain("cream");
    // enhanced steps shown, original directions are not
    expect(container.textContent).toContain("Boil the pasta until al dente.");
    expect(container.textContent).not.toContain("Cook pasta.");

    act(() => {
      root.unmount();
    });
  });
});
