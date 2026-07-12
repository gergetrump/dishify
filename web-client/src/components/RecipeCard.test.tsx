import { MantineProvider } from "@mantine/core";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MemoryRouter } from "react-router-dom";
import { describe, expect, it } from "vitest";

import type { RecipeResult } from "../api/types";
import { RecipeCard } from "./RecipeCard";
import { formatIngredientName } from "../utils/ingredientFormatting";

const recipe: RecipeResult = {
  rank: 1,
  id: 3136,
  title: "Pasta With Spinach Sauce",
  score: 0.87,
  time_minutes: 30,
  reasoning: {
    positive: ["Uses spinach from your pantry."],
    negative: ["You may need cream."],
  },
  inventory_matched: ["spinach", "pasta"],
  inventory_missing: ["cream"],
};

describe("RecipeCard", () => {
  it("renders recommendation details and a recipe link", () => {
    const container = document.createElement("div");
    const root = createRoot(container);

    act(() => {
      root.render(
        <MantineProvider>
          <MemoryRouter future={{ v7_startTransition: true, v7_relativeSplatPath: true }}>
            <RecipeCard recipe={recipe} />
          </MemoryRouter>
        </MantineProvider>,
      );
    });

    expect(container.textContent).toContain("Pasta With Spinach Sauce");
    expect(container.textContent).toContain("87");
    expect(container.textContent).toContain("score");
    expect(container.textContent).toContain("Uses spinach from your pantry.");
    expect(container.textContent).toContain(`Need ${formatIngredientName("cream")}`);
    expect(container.querySelector("a")?.getAttribute("href")).toBe("/recipes/3136");

    act(() => {
      root.unmount();
    });
  });
});