import { describe, expect, it } from "vitest";

import { formatRestrictionLabel, restrictionSections } from "./restrictions";

describe("restriction metadata", () => {
  it("groups backend restriction tags into user-facing sections", () => {
    expect(restrictionSections.map((section) => section.id)).toEqual([
      "allergies",
      "diets",
      "religious-ethical",
      "medical-sensitivities",
      "ingredient-exclusions",
    ]);
  });

  it("formats restriction keys for chip labels", () => {
    expect(formatRestrictionLabel("nut_allergy")).toBe("Nut Allergy");
    expect(formatRestrictionLabel("low_fodmap")).toBe("Low Fodmap");
  });
});
