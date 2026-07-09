import { describe, expect, it } from "vitest";

import { formatIngredientName } from "./ingredientFormatting";

describe("formatIngredientName", () => {
  it("capitalizes the first letter", () => {
    expect(formatIngredientName("extra virgin olive oil")).toBe("Extra virgin olive oil");
    expect(formatIngredientName("  garlic  ")).toBe("Garlic");
  });
});
