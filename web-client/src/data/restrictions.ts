export type RestrictionSection = {
  id: string;
  title: string;
  description: string;
  tags: string[];
};

export const restrictionSections: RestrictionSection[] = [
  {
    id: "allergies",
    title: "Allergies",
    description: "Ingredients Dishify should strictly avoid.",
    tags: [
      "nut_allergy",
      "milk_allergy",
      "egg_allergy",
      "wheat_allergy",
      "soy_allergy",
      "fish_allergy",
      "shellfish_allergy",
      "sesame_allergy",
      "corn_allergy",
      "mustard_allergy",
      "celery_allergy",
      "lupin_allergy",
      "sulfite_allergy",
      "buckwheat_allergy",
      "stone_fruit_allergy",
      "garlic_allergy",
      "onion_allergy",
    ],
  },
  {
    id: "diets",
    title: "Diets",
    description: "Common diet patterns and nutrition goals.",
    tags: [
      "vegetarian",
      "vegan",
      "lacto_ovo_vegetarian",
      "lacto_vegetarian",
      "ovo_vegetarian",
      "pescatarian",
      "flexitarian",
      "keto",
      "paleo",
      "low_carb",
      "low_fat",
      "low_sodium",
      "low_cholesterol",
      "no_added_sugar",
      "diabetic_diet",
      "renal_diet",
      "low_purine",
    ],
  },
  {
    id: "religious-ethical",
    title: "Religious and Ethical",
    description: "Religious and ethical food rules.",
    tags: [
      "halal",
      "kosher",
      "hindu_vegetarian",
      "buddhist_vegetarian",
      "jain",
      "no_beef",
      "no_pork",
      "no_red_meat",
      "no_honey",
      "no_gelatin",
      "no_alcohol",
    ],
  },
  {
    id: "medical-sensitivities",
    title: "Medical and Sensitivities",
    description: "Sensitivity and medical filters from the backend vocabulary.",
    tags: [
      "celiac_disease",
      "gluten_intolerance",
      "lactose_intolerance",
      "fodmap_intolerance",
      "fructose_intolerance",
      "histamine_intolerance",
      "low_fodmap",
      "low_histamine",
      "tyramine_sensitivity",
      "salicylate_sensitivity",
      "sulfite_sensitivity",
      "caffeine_sensitivity",
      "msg_sensitivity",
      "latex_food_syndrome",
      "alpha_gal_syndrome",
      "pku_diet",
      "aip_autoimmune_protocol",
      "artificial_sweetener_intolerance",
    ],
  },
  {
    id: "ingredient-exclusions",
    title: "Ingredient Exclusions",
    description: "Broad ingredient families to exclude.",
    tags: [
      "gluten_free",
      "dairy_free",
      "egg_free",
      "soy_free",
      "nut_free",
      "corn_free",
      "no_shellfish",
      "no_caffeine",
      "no_artificial_additives",
    ],
  },
];

export function formatRestrictionLabel(value: string) {
  return value
    .split("_")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}
