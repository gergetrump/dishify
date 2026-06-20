import SwiftUI

struct ResultDetailView: View {
    let result: RecipeResult

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
                headerSection

                if let summary = result.summary, !summary.isEmpty {
                    detailSection(title: "Summary") {
                        Text(summary)
                            .font(Theme.Typography.body)
                            .foregroundStyle(Theme.Colors.textPrimary)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                }

                if let reasoning = result.reasoning {
                    reasoningSection(reasoning)
                }

                if !result.inventoryMatched.isEmpty || !result.inventoryMissing.isEmpty {
                    inventorySection
                }

                if !result.directions.isEmpty {
                    directionsSection
                }
            }
            .padding(Theme.Spacing.md)
            .frame(maxWidth: Theme.Layout.contentMaxWidth)
            .frame(maxWidth: .infinity, alignment: .leading)
        }
        .background(Theme.Colors.background)
        .navigationTitle(result.title)
        .navigationBarTitleDisplayMode(.inline)
    }

    private var headerSection: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
            Text(RecipeResultFormatting.matchLabel(for: result.score))
                .font(Theme.Typography.headline)
                .foregroundStyle(Theme.Colors.accent)

            ProgressView(value: min(max(result.score, 0), 1))
                .tint(Theme.Colors.accent)
                .accessibilityLabel("Match score")
                .accessibilityValue(RecipeResultFormatting.matchLabel(for: result.score))

            if let minutes = result.timeMinutes {
                Label(
                    RecipeResultFormatting.durationLabel(for: minutes),
                    systemImage: "clock"
                )
                .font(Theme.Typography.body)
                .foregroundStyle(Theme.Colors.textSecondary)
                .accessibilityLabel("Cooking time")
                .accessibilityValue(RecipeResultFormatting.durationLabel(for: minutes))
            }
        }
        .surfaceCard()
    }

    private func reasoningSection(_ reasoning: Reasoning) -> some View {
        detailSection(title: "Why this recipe") {
            VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
                if reasoning.positive.isEmpty && reasoning.negative.isEmpty {
                    Text("No explanation was provided for this result.")
                        .font(Theme.Typography.body)
                        .foregroundStyle(Theme.Colors.textSecondary)
                } else {
                    ForEach(reasoning.positive, id: \.self) { item in
                        reasoningRow(symbol: "checkmark.circle.fill", text: item, color: Theme.Colors.success, trait: "Positive")
                    }

                    ForEach(reasoning.negative, id: \.self) { item in
                        reasoningRow(symbol: "xmark.circle.fill", text: item, color: Theme.Colors.error, trait: "Negative")
                    }
                }
            }
        }
    }

    private var inventorySection: some View {
        detailSection(title: "Your pantry") {
            VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
                if !result.inventoryMatched.isEmpty {
                    inventoryGroup(title: "Matched", items: result.inventoryMatched, color: Theme.Colors.success)
                }

                if !result.inventoryMissing.isEmpty {
                    inventoryGroup(title: "Missing", items: result.inventoryMissing, color: Theme.Colors.error)
                }
            }
        }
    }

    private var directionsSection: some View {
        detailSection(title: "Directions") {
            VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
                ForEach(Array(result.directions.enumerated()), id: \.offset) { index, step in
                    HStack(alignment: .top, spacing: Theme.Spacing.sm) {
                        Text("\(index + 1).")
                            .font(Theme.Typography.body.weight(.semibold))
                            .foregroundStyle(Theme.Colors.accent)
                            .frame(width: 28, alignment: .leading)
                            .accessibilityHidden(true)

                        Text(step)
                            .font(Theme.Typography.body)
                            .foregroundStyle(Theme.Colors.textPrimary)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .fixedSize(horizontal: false, vertical: true)
                    }
                    .accessibilityElement(children: .combine)
                    .accessibilityLabel("Step \(index + 1), \(step)")
                }
            }
        }
    }

    private func detailSection<Content: View>(title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
            Text(title)
                .font(Theme.Typography.headline)
                .foregroundStyle(Theme.Colors.textPrimary)
                .accessibilityAddTraits(.isHeader)

            content()
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .surfaceCard()
    }

    private func reasoningRow(symbol: String, text: String, color: Color, trait: String) -> some View {
        HStack(alignment: .top, spacing: Theme.Spacing.sm) {
            Image(systemName: symbol)
                .foregroundStyle(color)
                .frame(width: 20)
                .accessibilityHidden(true)

            Text(text)
                .font(Theme.Typography.body)
                .foregroundStyle(Theme.Colors.textPrimary)
                .frame(maxWidth: .infinity, alignment: .leading)
                .fixedSize(horizontal: false, vertical: true)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(trait): \(text)")
    }

    private func inventoryGroup(title: String, items: [String], color: Color) -> some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
            Text(title)
                .font(Theme.Typography.caption.weight(.semibold))
                .foregroundStyle(color)

            Text(items.joined(separator: ", "))
                .font(Theme.Typography.body)
                .foregroundStyle(Theme.Colors.textPrimary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .accessibilityElement(children: .combine)
        .accessibilityLabel("\(title) ingredients: \(items.joined(separator: ", "))")
    }
}

enum ResultDetailPreviewData {
    static let sample = RecipeResult(
        rank: 1,
        id: 3136,
        title: "Pasta With Spinach Sauce",
        summary: nil,
        timeMinutes: nil,
        score: 0.59,
        reasoning: Reasoning(
            positive: ["Uses penne and spinach from your pantry."],
            negative: ["Requires bacon and whipping cream."]
        ),
        directions: ["Cook pasta as directed.", "Combine spinach and sauce."],
        inventoryMatched: ["penne", "spinach"],
        inventoryMissing: ["bacon", "whipping cream"]
    )
}

#Preview {
    NavigationStack {
        ResultDetailView(result: ResultDetailPreviewData.sample)
    }
}
