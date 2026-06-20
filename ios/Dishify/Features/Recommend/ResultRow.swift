import SwiftUI

struct ResultRow: View {
    let result: RecipeResult

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
            HStack(alignment: .top, spacing: Theme.Spacing.sm) {
                VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                    Text("#\(result.rank)")
                        .font(Theme.Typography.caption)
                        .foregroundStyle(Theme.Colors.textSecondary)

                    Text(result.title)
                        .font(Theme.Typography.headline)
                        .foregroundStyle(Theme.Colors.textPrimary)
                        .multilineTextAlignment(.leading)
                        .fixedSize(horizontal: false, vertical: true)
                }

                Spacer(minLength: Theme.Spacing.sm)

                scoreBadge
            }

            ProgressView(value: min(max(result.score, 0), 1))
                .tint(Theme.Colors.accent)
                .accessibilityLabel("Match score")
                .accessibilityValue(RecipeResultFormatting.matchLabel(for: result.score))

            if !inventorySummary.isEmpty {
                Text(inventorySummary)
                    .font(Theme.Typography.caption)
                    .foregroundStyle(Theme.Colors.textSecondary)
            }
        }
        .padding(Theme.Spacing.md)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.Colors.surface)
        .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.md))
        .overlay(
            RoundedRectangle(cornerRadius: Theme.Radius.md)
                .stroke(Theme.Colors.border.opacity(0.6), lineWidth: 1)
        )
    }

    private var scoreBadge: some View {
        Text(RecipeResultFormatting.matchLabel(for: result.score))
            .font(Theme.Typography.caption.weight(.semibold))
            .foregroundStyle(Theme.Colors.primaryActionText)
            .padding(.horizontal, Theme.Spacing.sm)
            .padding(.vertical, Theme.Spacing.xs)
            .background(Theme.Colors.accent)
            .clipShape(Capsule())
            .accessibilityHidden(true)
    }

    private var inventorySummary: String {
        var parts: [String] = []
        if !result.inventoryMatched.isEmpty {
            parts.append("\(result.inventoryMatched.count) matched")
        }
        if !result.inventoryMissing.isEmpty {
            parts.append("\(result.inventoryMissing.count) missing")
        }
        return parts.joined(separator: " · ")
    }
}

enum RecipeResultFormatting {
    static func matchLabel(for score: Double) -> String {
        String(format: "%.0f%% match", score * 100)
    }

    static func durationLabel(for minutes: Int) -> String {
        minutes == 1 ? "1 minute" : "\(minutes) minutes"
    }
}

#Preview {
    ResultRow(result: ResultDetailPreviewData.sample)
        .padding()
        .background(Theme.Colors.background)
}
