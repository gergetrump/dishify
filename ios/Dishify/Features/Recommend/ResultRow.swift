import SwiftUI

struct RecipeCard: View {
    @EnvironmentObject private var router: AppRouter
    let recipe: RecipeResult

    private var score: Int { Int((recipe.score * 100).rounded()) }
    private var matched: [String] { recipe.inventoryMatched ?? [] }
    private var missing: [String] { recipe.inventoryMissing ?? [] }

    var body: some View {
        VStack(alignment: .leading, spacing: 14) {
            HStack(alignment: .top, spacing: 16) {
                VStack(alignment: .leading, spacing: 6) {
                    Eyebrow(text: "Rank \(recipe.rank)")
                    Text(recipe.title ?? "Untitled recipe")
                        .font(.system(size: 22, weight: .black))
                        .foregroundStyle(Theme.Colors.text)
                    HStack(spacing: 10) {
                        if let minutes = recipe.timeMinutes {
                            MetaPill(text: "\(minutes) min")
                        }
                        MetaPill(text: "Score \(score)")
                    }
                }
                Spacer()
                Text("\(score)")
                    .font(.system(size: 28, weight: .black))
                    .foregroundStyle(Theme.Colors.green)
            }

            if let summary = recipe.summary {
                Text(summary)
                    .foregroundStyle(Theme.Colors.muted)
            }

            reasoningPreview
            tagList

            HStack {
                Text("\(matched.count) matched")
                Text("\(missing.count) missing")
                Spacer()
                Button("View recipe") {
                    router.go(.recipe(recipe.id))
                }
                .font(.system(size: 15, weight: .bold))
                .foregroundStyle(Theme.Colors.primaryDark)
            }
            .font(.system(size: 14, weight: .heavy))
            .foregroundStyle(Theme.Colors.muted)
        }
        .padding(20)
        .background(Theme.Colors.surface)
        .overlay(
            RoundedRectangle(cornerRadius: 8)
                .stroke(Theme.Colors.border, lineWidth: 1)
        )
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }

    @ViewBuilder
    private var reasoningPreview: some View {
        let positive = recipe.reasoning?.positive ?? []
        let negative = recipe.reasoning?.negative ?? []
        if !positive.isEmpty || !negative.isEmpty {
            VStack(alignment: .leading, spacing: 12) {
                if !positive.isEmpty {
                    ReasoningBlock(title: "Why it fits", items: Array(positive.prefix(2)))
                }
                if !negative.isEmpty {
                    ReasoningBlock(title: "Watch for", items: Array(negative.prefix(2)))
                }
            }
        }
    }

    private var tagList: some View {
        let visibleTags = Array(matched.prefix(4)) + Array(missing.prefix(4))
        return FlowLayout(visibleTags, spacing: 8) { item in
            let isMatched = matched.prefix(4).contains(item)
            Text("\(isMatched ? "Have" : "Need") \(item)")
                .font(.system(size: 13, weight: .heavy))
                .foregroundStyle(isMatched ? Theme.Colors.green : Theme.Colors.primaryDark)
                .padding(.horizontal, 10)
                .padding(.vertical, 7)
                .background(isMatched ? Color(red: 0.898, green: 0.957, blue: 0.914) : Color(red: 1, green: 0.945, blue: 0.918))
                .clipShape(Capsule())
        }
    }
}

private struct ReasoningBlock: View {
    let title: String
    let items: [String]

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(title)
                .font(.system(size: 14, weight: .black))
            ForEach(items, id: \.self) { item in
                Text("• \(item)")
                    .font(.system(size: 14))
                    .foregroundStyle(Theme.Colors.muted)
            }
        }
    }
}

struct MetaPill: View {
    let text: String

    var body: some View {
        Text(text)
            .font(.system(size: 13, weight: .heavy))
            .foregroundStyle(Theme.Colors.muted)
    }
}
