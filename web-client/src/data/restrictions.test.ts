import { describe, expect, it } from "vitest";

import { formatRestrictionLabel, restrictionSections, restrictionTags } from "./restrictions";

describe("restriction metadata", () => {
  it("groups backend restriction tags into user-facing sections", () => {
    expect(restrictionSections.map((section) => section.id)).toEqual([
      "allergies",
      "diets",
      "religious-ethical",
      "medical-sensitivities",
      "ingredient-exclusions",
    ]);
    expect(restrictionTags).toContain("nut_allergy");
    expect(restrictionTags).toContain("vegetarian");
    expect(restrictionTags).toContain("halal");
  });

  it("formats restriction keys for chip labels", () => {
    expect(formatRestrictionLabel("nut_allergy")).toBe("Nut Allergy");
    expect(formatRestrictionLabel("low_fodmap")).toBe("Low Fodmap");
  });
});
