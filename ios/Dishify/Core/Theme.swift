import SwiftUI

enum Theme {
    enum Colors {
        static let background = Color("Background")
        static let surface = Color("Surface")
        static let textPrimary = Color("TextPrimary")
        static let textSecondary = Color("TextSecondary")
        static let accent = Color("AccentColor")
        static let primaryAction = Color("PrimaryAction")
        static let primaryActionText = Color("PrimaryActionText")
        static let border = Color("Border")
        static let success = Color("Success")
        static let error = Color("Error")
    }

    enum Spacing {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 16
        static let lg: CGFloat = 24
        static let xl: CGFloat = 32
    }

    enum Radius {
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 16
    }

    enum Layout {
        static let minTapTarget: CGFloat = 44
        static let contentMaxWidth: CGFloat = 720
    }

    enum Typography {
        static let largeTitle = Font.largeTitle.weight(.bold)
        static let title = Font.title2.weight(.bold)
        static let headline = Font.headline
        static let body = Font.body
        static let caption = Font.caption
        static let footnote = Font.footnote
    }
}

struct SurfaceCardModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(Theme.Spacing.md)
            .frame(maxWidth: .infinity, alignment: .leading)
            .background(Theme.Colors.surface)
            .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.md))
            .overlay(
                RoundedRectangle(cornerRadius: Theme.Radius.md)
                    .stroke(Theme.Colors.border.opacity(0.6), lineWidth: 1)
            )
    }
}

struct ThemedFieldModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(Theme.Spacing.sm)
            .background(Theme.Colors.surface)
            .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.sm))
            .overlay(
                RoundedRectangle(cornerRadius: Theme.Radius.sm)
                    .stroke(Theme.Colors.border, lineWidth: 1)
            )
    }
}

struct PrimaryButtonStyle: ButtonStyle {
    var isLoading = false

    func makeBody(configuration: Configuration) -> some View {
        HStack(spacing: Theme.Spacing.sm) {
            if isLoading {
                ProgressView()
                    .tint(Theme.Colors.primaryActionText)
            }
            configuration.label
                .font(Theme.Typography.headline)
        }
        .foregroundStyle(Theme.Colors.primaryActionText)
        .frame(maxWidth: .infinity, minHeight: Theme.Layout.minTapTarget)
        .background(Theme.Colors.primaryAction.opacity(configuration.isPressed ? 0.85 : 1))
        .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.md))
        .animation(.easeOut(duration: 0.15), value: configuration.isPressed)
    }
}

extension View {
    func surfaceCard() -> some View {
        modifier(SurfaceCardModifier())
    }

    func themedField() -> some View {
        modifier(ThemedFieldModifier())
    }
}
