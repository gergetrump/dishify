import type { ParsedIngredient } from "../api/types";
import { formatIngredientName } from "../utils/ingredientFormatting";

const PANTRY_KEY = "dishify.pantry";

export type PantryItem = ParsedIngredient & {
  id: string;
};

export function loadPantryItems(): PantryItem[] {
  const raw = window.localStorage.getItem(PANTRY_KEY);
  if (!raw) {
    return [];
  }

  try {
    const parsed = JSON.parse(raw);
    if (!Array.isArray(parsed)) {
      return [];
    }
    return parsed.filter(isPantryItem);
  } catch {
    return [];
  }
}

export function savePantryItems(items: PantryItem[]) {
  window.localStorage.setItem(PANTRY_KEY, JSON.stringify(items));
}

export function pantryItemsToIngredients(items: PantryItem[]): ParsedIngredient[] {
  return items.map(({ id: _id, ...ingredient }) => ingredient);
}

export function createPantryItem(input: {
  name: string;
  quantity?: number | null;
  unit?: string | null;
}): PantryItem {
  const name = formatIngredientName(input.name);
  return {
    id: crypto.randomUUID(),
    name,
    quantity: input.quantity ?? null,
    unit: input.unit?.trim() || null,
    raw_text: rawTextForIngredient(name, input.quantity ?? null, input.unit ?? null),
  };
}

function rawTextForIngredient(name: string, quantity: number | null, unit: string | null) {
  const amount = quantity == null ? "" : String(quantity);
  const normalizedUnit = unit?.trim() ?? "";
  return [amount, normalizedUnit, name].filter(Boolean).join(" ");
}

function isPantryItem(value: unknown): value is PantryItem {
  if (!value || typeof value !== "object") {
    return false;
  }

  const candidate = value as Partial<PantryItem>;
  return typeof candidate.id === "string" && typeof candidate.name === "string";
}
