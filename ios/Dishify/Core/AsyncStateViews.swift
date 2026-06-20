import SwiftUI

struct LoadingStateView: View {
    let message: String

    var body: some View {
        VStack(spacing: Theme.Spacing.md) {
            ProgressView()
            Text(message)
                .font(Theme.Typography.body)
                .foregroundStyle(Theme.Colors.textSecondary)
                .multilineTextAlignment(.center)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.Colors.background)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(message)
    }
}

struct ErrorStateView: View {
    let message: String
    var retryTitle: String = "Retry"
    var onRetry: (() -> Void)?

    var body: some View {
        VStack(spacing: Theme.Spacing.md) {
            Image(systemName: "exclamationmark.triangle.fill")
                .font(.system(size: 32))
                .foregroundStyle(Theme.Colors.error)
                .accessibilityHidden(true)

            Text(message)
                .font(Theme.Typography.body)
                .foregroundStyle(Theme.Colors.error)
                .multilineTextAlignment(.center)

            if let onRetry {
                Button(retryTitle, action: onRetry)
                    .font(Theme.Typography.headline)
                    .frame(minHeight: Theme.Layout.minTapTarget)
                    .accessibilityHint("Attempts to load this screen again.")
            }
        }
        .padding(Theme.Spacing.lg)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.Colors.background)
        .accessibilityElement(children: .contain)
    }
}

struct EmptyStateView: View {
    let message: String

    var body: some View {
        Text(message)
            .font(Theme.Typography.body)
            .foregroundStyle(Theme.Colors.textSecondary)
            .frame(maxWidth: .infinity, alignment: .leading)
            .accessibilityLabel(message)
    }
}

struct ErrorBanner: View {
    let message: String

    var body: some View {
        Label(message, systemImage: "exclamationmark.circle.fill")
            .font(Theme.Typography.caption)
            .foregroundStyle(Theme.Colors.error)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(Theme.Spacing.sm)
            .background(Theme.Colors.surface)
            .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.sm))
            .accessibilityLabel("Error: \(message)")
    }
}

struct InlineLoadingRow: View {
    let message: String

    var body: some View {
        HStack(spacing: Theme.Spacing.sm) {
            ProgressView()
            Text(message)
                .font(Theme.Typography.body)
                .foregroundStyle(Theme.Colors.textSecondary)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .accessibilityElement(children: .combine)
        .accessibilityLabel(message)
    }
}

struct NoticeBanner: View {
    let message: String

    var body: some View {
        Label(message, systemImage: "info.circle")
            .font(Theme.Typography.caption)
            .foregroundStyle(Theme.Colors.textSecondary)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(Theme.Spacing.sm)
            .background(Theme.Colors.surface)
            .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.sm))
            .accessibilityLabel(message)
    }
}
