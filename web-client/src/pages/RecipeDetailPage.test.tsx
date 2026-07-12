import { describe, expect, it } from "vitest";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { act } from "react";
import { createRoot } from "react-dom/client";
import { MantineProvider } from "@mantine/core";
import { RecipeDetailPage } from "./RecipeDetailPage";
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

describe("RecipeDetailPage", () => {
  it("renders selected recipe details from route state", () => {
    const container = document.createElement("div");
    const root = createRoot(container);

    act(() => {
      root.render(
        <MantineProvider>
          <MemoryRouter
            future={{ v7_startTransition: true, v7_relativeSplatPath: true }}
            initialEntries={[{ pathname: "/recipes/3136", state: { recipe } }]}
          >
           <Routes>
              <Route path="/recipes/:id" element={<RecipeDetailPage />} />
            </Routes>
          </MemoryRouter>,
        </MantineProvider>
      );
    });

    expect(container.textContent).toContain("Pasta With Spinach Sauce");
    expect(container.textContent).toContain("Score 87");
    expect(container.textContent).toContain("Uses spinach from your pantry.");
    expect(container.textContent).toContain("Cook pasta.");
    expect(container.textContent).toContain("cream");

    act(() => {
      root.unmount();
    });
  });
});
