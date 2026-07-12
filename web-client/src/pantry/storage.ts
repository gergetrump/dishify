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
    id: generateId(),
    name,
    quantity: input.quantity ?? null,
    unit: input.unit?.trim() || null,
    raw_text: rawTextForIngredient(name, input.quantity ?? null, input.unit ?? null),
  };
}

// crypto.randomUUID() requires a secure context (HTTPS/localhost) and is
// undefined over plain HTTP, so fall back to crypto.getRandomValues (which
// has no such restriction) and finally to Math.random as a last resort.
function generateId(): string {
  if (typeof crypto !== "undefined" && typeof crypto.randomUUID === "function") {
    return crypto.randomUUID();
  }
  if (typeof crypto !== "undefined" && typeof crypto.getRandomValues === "function") {
    const bytes = crypto.getRandomValues(new Uint8Array(16));
    bytes[6] = (bytes[6] & 0x0f) | 0x40;
    bytes[8] = (bytes[8] & 0x3f) | 0x80;
    const hex = Array.from(bytes, (b) => b.toString(16).padStart(2, "0")).join("");
    return `${hex.slice(0, 8)}-${hex.slice(8, 12)}-${hex.slice(12, 16)}-${hex.slice(16, 20)}-${hex.slice(20)}`;
  }
  return `id-${Date.now()}-${Math.random().toString(16).slice(2)}`;
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
