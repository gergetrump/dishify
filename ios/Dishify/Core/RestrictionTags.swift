import Foundation

enum RestrictionCategory: String, CaseIterable, Identifiable {
    case allergies
    case dietsAndLifestyle

    var id: String { rawValue }

    var title: String {
        switch self {
        case .allergies:
            return "Allergies & Intolerances"
        case .dietsAndLifestyle:
            return "Diets & Lifestyle"
        }
    }
}

struct RestrictionTag: Identifiable, Hashable {
    let id: String
    let label: String
    let category: RestrictionCategory
}

enum RestrictionTags {
    /// Snapshot of top-level keys from `data/restriction_rules.json`.
    /// Keep in sync with the backend rules file when tags change.
    static let all: [RestrictionTag] = [
        RestrictionTag(id: "aip_autoimmune_protocol", label: "AIP (Autoimmune Protocol)", category: .dietsAndLifestyle),
        RestrictionTag(id: "alpha_gal_syndrome", label: "Alpha-Gal Syndrome", category: .allergies),
        RestrictionTag(id: "artificial_sweetener_intolerance", label: "Artificial Sweetener Intolerance", category: .allergies),
        RestrictionTag(id: "buckwheat_allergy", label: "Buckwheat Allergy", category: .allergies),
        RestrictionTag(id: "buddhist_vegetarian", label: "Buddhist Vegetarian", category: .dietsAndLifestyle),
        RestrictionTag(id: "caffeine_sensitivity", label: "Caffeine Sensitivity", category: .allergies),
        RestrictionTag(id: "celery_allergy", label: "Celery Allergy", category: .allergies),
        RestrictionTag(id: "celiac_disease", label: "Celiac Disease", category: .allergies),
        RestrictionTag(id: "corn_allergy", label: "Corn Allergy", category: .allergies),
        RestrictionTag(id: "corn_free", label: "Corn Free", category: .dietsAndLifestyle),
        RestrictionTag(id: "dairy_free", label: "Dairy Free", category: .dietsAndLifestyle),
        RestrictionTag(id: "diabetic_diet", label: "Diabetic Diet", category: .dietsAndLifestyle),
        RestrictionTag(id: "egg_allergy", label: "Egg Allergy", category: .allergies),
        RestrictionTag(id: "egg_free", label: "Egg Free", category: .dietsAndLifestyle),
        RestrictionTag(id: "fish_allergy", label: "Fish Allergy", category: .allergies),
        RestrictionTag(id: "flexitarian", label: "Flexitarian", category: .dietsAndLifestyle),
        RestrictionTag(id: "fodmap_intolerance", label: "FODMAP Intolerance", category: .allergies),
        RestrictionTag(id: "fructose_intolerance", label: "Fructose Intolerance", category: .allergies),
        RestrictionTag(id: "garlic_allergy", label: "Garlic Allergy", category: .allergies),
        RestrictionTag(id: "gluten_free", label: "Gluten Free", category: .dietsAndLifestyle),
        RestrictionTag(id: "gluten_intolerance", label: "Gluten Intolerance", category: .allergies),
        RestrictionTag(id: "halal", label: "Halal", category: .dietsAndLifestyle),
        RestrictionTag(id: "hindu_vegetarian", label: "Hindu Vegetarian", category: .dietsAndLifestyle),
        RestrictionTag(id: "histamine_intolerance", label: "Histamine Intolerance", category: .allergies),
        RestrictionTag(id: "jain", label: "Jain", category: .dietsAndLifestyle),
        RestrictionTag(id: "keto", label: "Keto", category: .dietsAndLifestyle),
        RestrictionTag(id: "kosher", label: "Kosher", category: .dietsAndLifestyle),
        RestrictionTag(id: "lacto_ovo_vegetarian", label: "Lacto-Ovo Vegetarian", category: .dietsAndLifestyle),
        RestrictionTag(id: "lacto_vegetarian", label: "Lacto Vegetarian", category: .dietsAndLifestyle),
        RestrictionTag(id: "lactose_intolerance", label: "Lactose Intolerance", category: .allergies),
        RestrictionTag(id: "latex_food_syndrome", label: "Latex Food Syndrome", category: .allergies),
        RestrictionTag(id: "low_carb", label: "Low Carb", category: .dietsAndLifestyle),
        RestrictionTag(id: "low_cholesterol", label: "Low Cholesterol", category: .dietsAndLifestyle),
        RestrictionTag(id: "low_fat", label: "Low Fat", category: .dietsAndLifestyle),
        RestrictionTag(id: "low_fodmap", label: "Low FODMAP", category: .dietsAndLifestyle),
        RestrictionTag(id: "low_histamine", label: "Low Histamine", category: .dietsAndLifestyle),
        RestrictionTag(id: "low_purine", label: "Low Purine", category: .dietsAndLifestyle),
        RestrictionTag(id: "low_sodium", label: "Low Sodium", category: .dietsAndLifestyle),
        RestrictionTag(id: "lupin_allergy", label: "Lupin Allergy", category: .allergies),
        RestrictionTag(id: "milk_allergy", label: "Milk Allergy", category: .allergies),
        RestrictionTag(id: "msg_sensitivity", label: "MSG Sensitivity", category: .allergies),
        RestrictionTag(id: "mustard_allergy", label: "Mustard Allergy", category: .allergies),
        RestrictionTag(id: "no_added_sugar", label: "No Added Sugar", category: .dietsAndLifestyle),
        RestrictionTag(id: "no_alcohol", label: "No Alcohol", category: .dietsAndLifestyle),
        RestrictionTag(id: "no_artificial_additives", label: "No Artificial Additives", category: .dietsAndLifestyle),
        RestrictionTag(id: "no_beef", label: "No Beef", category: .dietsAndLifestyle),
        RestrictionTag(id: "no_caffeine", label: "No Caffeine", category: .dietsAndLifestyle),
        RestrictionTag(id: "no_gelatin", label: "No Gelatin", category: .dietsAndLifestyle),
        RestrictionTag(id: "no_honey", label: "No Honey", category: .dietsAndLifestyle),
        RestrictionTag(id: "no_pork", label: "No Pork", category: .dietsAndLifestyle),
        RestrictionTag(id: "no_red_meat", label: "No Red Meat", category: .dietsAndLifestyle),
        RestrictionTag(id: "no_shellfish", label: "No Shellfish", category: .dietsAndLifestyle),
        RestrictionTag(id: "nut_allergy", label: "Nut Allergy", category: .allergies),
        RestrictionTag(id: "nut_free", label: "Nut Free", category: .dietsAndLifestyle),
        RestrictionTag(id: "onion_allergy", label: "Onion Allergy", category: .allergies),
        RestrictionTag(id: "ovo_vegetarian", label: "Ovo Vegetarian", category: .dietsAndLifestyle),
        RestrictionTag(id: "paleo", label: "Paleo", category: .dietsAndLifestyle),
        RestrictionTag(id: "pescatarian", label: "Pescatarian", category: .dietsAndLifestyle),
        RestrictionTag(id: "pku_diet", label: "PKU Diet", category: .dietsAndLifestyle),
        RestrictionTag(id: "renal_diet", label: "Renal Diet", category: .dietsAndLifestyle),
        RestrictionTag(id: "salicylate_sensitivity", label: "Salicylate Sensitivity", category: .allergies),
        RestrictionTag(id: "sesame_allergy", label: "Sesame Allergy", category: .allergies),
        RestrictionTag(id: "shellfish_allergy", label: "Shellfish Allergy", category: .allergies),
        RestrictionTag(id: "soy_allergy", label: "Soy Allergy", category: .allergies),
        RestrictionTag(id: "soy_free", label: "Soy Free", category: .dietsAndLifestyle),
        RestrictionTag(id: "stone_fruit_allergy", label: "Stone Fruit Allergy", category: .allergies),
        RestrictionTag(id: "sulfite_allergy", label: "Sulfite Allergy", category: .allergies),
        RestrictionTag(id: "sulfite_sensitivity", label: "Sulfite Sensitivity", category: .allergies),
        RestrictionTag(id: "tyramine_sensitivity", label: "Tyramine Sensitivity", category: .allergies),
        RestrictionTag(id: "vegan", label: "Vegan", category: .dietsAndLifestyle),
        RestrictionTag(id: "vegetarian", label: "Vegetarian", category: .dietsAndLifestyle),
        RestrictionTag(id: "wheat_allergy", label: "Wheat Allergy", category: .allergies),
    ]

    static func grouped(matching searchText: String = "") -> [(RestrictionCategory, [RestrictionTag])] {
        let query = searchText.trimmingCharacters(in: .whitespacesAndNewlines).lowercased()
        let filtered = all.filter { tag in
            query.isEmpty ||
            tag.label.lowercased().contains(query) ||
            tag.id.lowercased().contains(query)
        }

        return RestrictionCategory.allCases.compactMap { category in
            let tags = filtered
                .filter { $0.category == category }
                .sorted { $0.label.localizedCaseInsensitiveCompare($1.label) == .orderedAscending }
            return tags.isEmpty ? nil : (category, tags)
        }
    }
}

