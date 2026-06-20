import { beforeEach, describe, expect, it, vi } from "vitest";

import {
  createPantryItem,
  loadPantryItems,
  pantryItemsToIngredients,
  savePantryItems,
  type PantryItem,
} from "./storage";

describe("pantry storage", () => {
  beforeEach(() => {
    window.localStorage.clear();
    vi.stubGlobal("crypto", {
      randomUUID: () => "test-id",
    });
  });

  it("creates normalized pantry items for the API", () => {
    const item = createPantryItem({
      name: "  Eggs  ",
      quantity: 2,
      unit: " pieces ",
    });

    expect(item).toEqual({
      id: "test-id",
      name: "Eggs",
      quantity: 2,
      unit: "pieces",
      raw_text: "2 pieces Eggs",
    });
  });

  it("persists and loads valid pantry items", () => {
    const items: PantryItem[] = [
      {
        id: "eggs",
        name: "Eggs",
        quantity: 2,
        unit: "pieces",
        raw_text: "2 pieces Eggs",
      },
    ];

    savePantryItems(items);

    expect(loadPantryItems()).toEqual(items);
  });

  it("ignores malformed stored pantry values", () => {
    window.localStorage.setItem(
      "dishify.pantry",
      JSON.stringify([{ name: "Eggs" }, { id: "valid", name: "Spinach" }]),
    );

    expect(loadPantryItems()).toEqual([{ id: "valid", name: "Spinach" }]);
  });

  it("removes local ids when converting to backend ingredients", () => {
    const ingredients = pantryItemsToIngredients([
      {
        id: "eggs",
        name: "Eggs",
        quantity: 2,
        unit: "pieces",
        raw_text: "2 pieces Eggs",
      },
    ]);

    expect(ingredients).toEqual([
      {
        name: "Eggs",
        quantity: 2,
        unit: "pieces",
        raw_text: "2 pieces Eggs",
      },
    ]);
  });
});
