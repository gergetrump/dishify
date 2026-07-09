import SwiftUI

struct RecipeDetailPage: View {
    @EnvironmentObject private var router: AppRouter
    let recipeID: Int

    @State private var augmented: AugmentResponse?

    private var recipe: RecipeResult? {
        RecommendationStore.findRecipe(id: recipeID)
    }

    var body: some View {
        if let recipe {
            detail(recipe)
                .task(id: recipe.id) {
                    await loadAugment(for: recipe)
                }
        } else {
            VStack(alignment: .leading, spacing: 16) {
                Eyebrow(text: "Recipe")
                Text("Recipe not found")
                    .font(.system(size: 40, weight: .black))
                Text("Recipe detail is available after choosing a recommendation from the latest results.")
                    .foregroundStyle(Theme.Colors.muted)
                Button("Back to results") {
                    router.go(.results)
                }
                .buttonStyle(PrimaryButtonStyle())
            }
            .surfacePanel()
        }
    }

    private func detail(_ recipe: RecipeResult) -> some View {
        VStack(alignment: .leading, spacing: 24) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 8) {
                    Eyebrow(text: "Recipe")
                    Text(recipe.title ?? "Untitled recipe")
                        .font(.system(size: 40, weight: .black))
                    HStack(spacing: 10) {
                        if let minutes = recipe.timeMinutes {
                            MetaPill(text: "\(minutes) min")
                        }
                        MetaPill(text: "Score \(Int((recipe.score * 100).rounded()))")
                        MetaPill(text: "Rank \(recipe.rank)")
                    }
                }
                Spacer()
                Button("Back to results") {
                    router.go(.results)
                }
                .font(.system(size: 15, weight: .bold))
                .foregroundStyle(Theme.Colors.primaryDark)
            }

            if let summary = recipe.summary {
                Text(summary)
                    .font(.system(size: 18, weight: .semibold))
                    .foregroundStyle(Theme.Colors.muted)
            }

            VStack(spacing: 16) {
                DetailPanel(title: "Ingredient match") {
                    TagSection(title: "You have", items: recipe.inventoryMatched ?? [], empty: "No matched ingredients returned.")
                    TagSection(title: "You may need", items: recipe.inventoryMissing ?? [], empty: "No missing ingredients returned.")
                }
                DetailPanel(title: "Reasoning") {
                    BulletSection(title: "Why it fits", items: recipe.reasoning?.positive ?? [], empty: "No positive reasoning returned.")
                    BulletSection(title: "Watch for", items: recipe.reasoning?.negative ?? [], empty: "No concerns returned.")
                }
            }

            DetailPanel(title: "Directions") {
                if let augmented {
                    augmentedDirections(augmented)
                } else if let directions = recipe.directions, !directions.isEmpty {
                    corpusDirections(directions)
                } else {
                    EmptyState(text: "No directions were returned for this recipe.")
                }
            }
        }
        .surfacePanel()
    }

    private func loadAugment(for recipe: RecipeResult) async {
        augmented = nil
        let pending = AugmentCache.get(recipeId: recipe.id) ?? AugmentCache.prefetch(recipe)
        guard let pending else { return }
        do {
            augmented = try await pending.value
        } catch {
            AugmentCache.remove(recipeId: recipe.id)
        }
    }

    @ViewBuilder
    private func augmentedDirections(_ augmented: AugmentResponse) -> some View {
        VStack(alignment: .leading, spacing: 12) {
            if let minutes = augmented.estimatedTimeMinutes {
                Text("Estimated total: \(minutes) min")
                    .font(.system(size: 15))
                    .foregroundStyle(Theme.Colors.muted)
            }
            VStack(alignment: .leading, spacing: 14) {
                ForEach(Array(augmented.steps.enumerated()), id: \.offset) { index, step in
                    VStack(alignment: .leading, spacing: 4) {
                        HStack(alignment: .top, spacing: 10) {
                            Text("\(index + 1).")
                                .font(.system(size: 15, weight: .black))
                            VStack(alignment: .leading, spacing: 4) {
                                Text(step.text)
                                if let duration = step.durationMinutes {
                                    Text("~\(duration) min")
                                        .font(.system(size: 14))
                                        .foregroundStyle(Theme.Colors.muted)
                                        .italic()
                                }
                                if let tip = step.tip, !tip.isEmpty {
                                    Text("Tip: \(tip)")
                                        .font(.system(size: 14))
                                        .foregroundStyle(Theme.Colors.muted)
                                }
                            }
                        }
                    }
                }
            }
            if !augmented.tips.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Tips")
                        .font(.system(size: 16, weight: .black))
                    ForEach(augmented.tips, id: \.self) { tip in
                        Text("• \(tip)")
                            .font(.system(size: 14))
                            .foregroundStyle(Theme.Colors.muted)
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func corpusDirections(_ directions: [String]) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            ForEach(Array(directions.enumerated()), id: \.offset) { index, step in
                HStack(alignment: .top, spacing: 10) {
                    Text("\(index + 1).")
                        .font(.system(size: 15, weight: .black))
                    Text(step)
                }
            }
        }
    }
}

private struct DetailPanel<Content: View>: View {
    let title: String
    @ViewBuilder let content: Content

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            Text(title)
                .font(.system(size: 20, weight: .black))
            content
        }
        .padding(18)
        .background(Color(red: 0.980, green: 0.969, blue: 0.949))
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Theme.Colors.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}

private struct TagSection: View {
    let title: String
    let items: [String]
    let empty: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.system(size: 15, weight: .black))
            if items.isEmpty {
                Text(empty).foregroundStyle(Theme.Colors.muted)
            } else {
                FlowLayout(items, spacing: 8) { item in
                    Text(item)
                        .font(.system(size: 13, weight: .heavy))
                        .foregroundStyle(Theme.Colors.green)
                        .padding(.horizontal, 10)
                        .padding(.vertical, 7)
                        .background(Color(red: 0.898, green: 0.957, blue: 0.914))
                        .clipShape(Capsule())
                }
            }
        }
    }
}

private struct BulletSection: View {
    let title: String
    let items: [String]
    let empty: String

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.system(size: 15, weight: .black))
            if items.isEmpty {
                Text(empty).foregroundStyle(Theme.Colors.muted)
            } else {
                ForEach(items, id: \.self) { item in
                    Text("• \(item)")
                        .foregroundStyle(Theme.Colors.muted)
                }
            }
        }
    }
}
