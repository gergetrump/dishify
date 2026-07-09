import SwiftUI

struct RecipeDetailPage: View {
    @EnvironmentObject private var router: AppRouter
    let recipeID: Int

    @State private var augmented: AugmentResponse?
    @State private var isLoadingAugment = false

    private var recipe: RecipeResult? {
        RecommendationStore.findRecipe(id: recipeID)
    }

    var body: some View {
        VStack(spacing: 0) {
            if let recipe {
                header
                ScrollView {
                    detailContent(recipe)
                        .padding(.horizontal, Theme.Spacing.screenPadding)
                        .padding(.bottom, Theme.Spacing.xxl)
                }
                .task(id: recipe.id) {
                    await loadAugment(for: recipe)
                }
            } else {
                notFoundView
            }
        }
        .screenBackground()
        .navigationBarHidden(true)
    }

    private var header: some View {
        HStack {
            Button {
                router.pop()
            } label: {
                Text("Back")
                    .font(Theme.Fonts.label(16, weight: .semibold))
                    .foregroundStyle(Theme.Colors.primary)
            }
            Spacer()
            Text("Recipe")
                .font(Theme.Fonts.display(18, weight: .bold))
                .foregroundStyle(Theme.Colors.text)
            Spacer()
            ProfileToolbarButton { router.push(.profile) }
        }
        .padding(.horizontal, Theme.Spacing.screenPadding)
        .padding(.vertical, Theme.Spacing.md)
    }

    private func detailContent(_ recipe: RecipeResult) -> some View {
        let score = Int((recipe.score * 100).rounded())
        return VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
            VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
                Text(recipe.title ?? "Untitled recipe")
                    .font(Theme.Fonts.display(28, weight: .bold))
                    .foregroundStyle(Theme.Colors.text)
                RecipeMetaRow(timeMinutes: recipe.timeMinutes, score: score)
            }

            if let summary = recipe.summary {
                Text(summary)
                    .font(Theme.Fonts.body(16))
                    .foregroundStyle(Theme.Colors.muted)
            }

            ingredientsSection(recipe)
            directionsSection(recipe)
        }
    }

    private func ingredientsSection(_ recipe: RecipeResult) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.md) {
            Text("Ingredients")
                .font(Theme.Fonts.display(20, weight: .bold))

            VStack(spacing: 0) {
                let matched = recipe.inventoryMatched ?? []
                let missing = recipe.inventoryMissing ?? []

                ForEach(Array(matched.enumerated()), id: \.offset) { index, item in
                    ingredientRow(text: item, isMissing: false)
                    if index < matched.count - 1 || !missing.isEmpty {
                        Divider()
                    }
                }
                ForEach(Array(missing.enumerated()), id: \.offset) { index, item in
                    ingredientRow(text: item, isMissing: true)
                    if index < missing.count - 1 {
                        Divider()
                    }
                }
                if matched.isEmpty && missing.isEmpty {
                    Text("No ingredient match data returned.")
                        .font(Theme.Fonts.body(15))
                        .foregroundStyle(Theme.Colors.muted)
                        .padding(Theme.Spacing.lg)
                }
            }
            .background(Theme.Colors.cardBackground)
            .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.card))
        }
    }

    private func ingredientRow(text: String, isMissing: Bool) -> some View {
        HStack(alignment: .top, spacing: Theme.Spacing.sm) {
            if isMissing {
                MissingBadge()
            }
            VStack(alignment: .leading, spacing: 2) {
                Text(text)
                    .font(Theme.Fonts.label(15, weight: .semibold))
                    .foregroundStyle(Theme.Colors.text)
            }
            Spacer()
        }
        .padding(Theme.Spacing.lg)
    }

    @ViewBuilder
    private func directionsSection(_ recipe: RecipeResult) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.md) {
            Text("Instructions")
                .font(Theme.Fonts.display(20, weight: .bold))

            if isLoadingAugment && augmented == nil {
                LoadingState(message: "Preparing directions...")
            } else if let augmented {
                augmentedDirections(augmented)
            } else if let directions = recipe.directions, !directions.isEmpty {
                corpusDirections(directions)
            } else {
                EmptyState(text: "No directions were returned for this recipe.")
            }
        }
    }

    private var notFoundView: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
            header
            Text("Recipe not found")
                .font(Theme.Fonts.display(24, weight: .bold))
            Text("Recipe detail is available after choosing a recommendation from the latest results.")
                .foregroundStyle(Theme.Colors.muted)
            Button("Back to results") {
                router.pop()
            }
            .buttonStyle(PrimaryButtonStyle())
            .padding(.horizontal, Theme.Spacing.screenPadding)
            Spacer()
        }
    }

    private func loadAugment(for recipe: RecipeResult) async {
        augmented = nil
        isLoadingAugment = true
        defer { isLoadingAugment = false }
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
        VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
            if let minutes = augmented.estimatedTimeMinutes {
                Text("Estimated total: \(minutes) min")
                    .font(Theme.Fonts.body(14))
                    .foregroundStyle(Theme.Colors.muted)
            }
            ForEach(Array(augmented.steps.enumerated()), id: \.offset) { index, step in
                StepRow(
                    number: index + 1,
                    text: step.text,
                    durationMinutes: step.durationMinutes,
                    tip: step.tip
                )
            }
            if !augmented.tips.isEmpty {
                VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
                    Text("Tips")
                        .font(Theme.Fonts.label(16, weight: .bold))
                    ForEach(augmented.tips, id: \.self) { tip in
                        Text("• \(tip)")
                            .font(Theme.Fonts.body(14))
                            .foregroundStyle(Theme.Colors.muted)
                    }
                }
            }
        }
    }

    @ViewBuilder
    private func corpusDirections(_ directions: [String]) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
            ForEach(Array(directions.enumerated()), id: \.offset) { index, step in
                StepRow(number: index + 1, text: step)
            }
        }
    }
}
