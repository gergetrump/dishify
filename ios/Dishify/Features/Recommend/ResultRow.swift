import SwiftUI

struct RecipeCard: View {
    @EnvironmentObject private var router: AppRouter
    let recipe: RecipeResult

    private var score: Int { Int((recipe.score * 100).rounded()) }
    private var matched: [String] { recipe.inventoryMatched ?? [] }
    private var missing: [String] { recipe.inventoryMissing ?? [] }

    var body: some View {
        Button {
            router.push(.recipe(recipe.id))
        } label: {
            VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                Text(recipe.title ?? "Untitled recipe")
                    .font(Theme.Fonts.display(20, weight: .bold))
                    .foregroundStyle(Theme.Colors.text)
                    .multilineTextAlignment(.leading)

                RecipeMetaRow(timeMinutes: recipe.timeMinutes, score: score)

                if let summary = recipe.summary {
                    Text(summary)
                        .font(Theme.Fonts.body(15))
                        .foregroundStyle(Theme.Colors.muted)
                        .multilineTextAlignment(.leading)
                } else {
                    Text(scoreSummary)
                        .font(Theme.Fonts.body(15))
                        .foregroundStyle(Theme.Colors.muted)
                        .multilineTextAlignment(.leading)
                }

                reasoningPreview
            }
            .padding(Theme.Spacing.lg)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Theme.Colors.cardBackground)
            .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.card))
        }
        .buttonStyle(.plain)
    }

    private var scoreSummary: String {
        let fit = score >= 80 ? "very good" : (score >= 60 ? "good" : "decent")
        let coverage = matched.count >= missing.count ? "most" : "many"
        let missingList = missing.prefix(3).map(IngredientFormatting.displayName).joined(separator: ", ")
        if missing.isEmpty {
            return "Score \(score): \(recipe.title ?? "This recipe") is a \(fit) fit with your pantry."
        }
        return "Score \(score): \(recipe.title ?? "This recipe") is a \(fit) fit since you already have \(coverage) ingredients. Missing: \(missingList)."
    }

    @ViewBuilder
    private var reasoningPreview: some View {
        let positive = recipe.reasoning?.positive ?? []
        if let first = positive.first {
            Text(first)
                .font(Theme.Fonts.body(14))
                .foregroundStyle(Theme.Colors.muted)
                .lineLimit(2)
        }
    }
}

private struct ReasoningBlock: View {
    let title: String
    let items: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(Theme.Fonts.label(14, weight: .bold))
            ForEach(items, id: \.self) { item in
                Text("• \(item)")
                    .font(Theme.Fonts.body(14))
                    .foregroundStyle(Theme.Colors.muted)
            }
        }
    }
}
