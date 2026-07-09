import SwiftUI

enum Theme {
    enum Colors {
        static let background = Color("Background")
        static let surface = Color("Surface")
        static let surfaceMuted = Color(red: 0.945, green: 0.925, blue: 0.902)
        static let text = Color("TextPrimary")
        static let muted = Color("TextSecondary")
        static let primary = Color("PrimaryAction")
        static let primaryDark = Color(red: 0.847, green: 0.263, blue: 0.110)
        static let green = Color(red: 0.184, green: 0.420, blue: 0.278)
        static let border = Color("Border")
        static let errorBackground = Color("Error").opacity(0.15)
        static let errorText = Color(red: 0.616, green: 0.165, blue: 0.067)
        static let successBackground = Color("Success").opacity(0.15)
        static let successText = Color(red: 0.137, green: 0.345, blue: 0.227)
        static let missing = Color(red: 0.812, green: 0.180, blue: 0.094)
        static let cardBackground = Color(red: 0.961, green: 0.957, blue: 0.949)
    }

    enum Spacing {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 16
        static let xl: CGFloat = 20
        static let xxl: CGFloat = 24
        static let screenPadding: CGFloat = 20
    }

    enum Radius {
        static let card: CGFloat = 12
        static let button: CGFloat = 12
        static let input: CGFloat = 12
    }

    enum Fonts {
        static func display(_ size: CGFloat, weight: Font.Weight = .bold) -> Font {
            .system(size: size, weight: weight, design: .serif)
        }

        static func body(_ size: CGFloat, weight: Font.Weight = .regular) -> Font {
            .system(size: size, weight: weight, design: .default)
        }

        static func label(_ size: CGFloat = 14, weight: Font.Weight = .semibold) -> Font {
            .system(size: size, weight: weight, design: .default)
        }
    }
}

struct SurfaceModifier: ViewModifier {
    var padded = true

    func body(content: Content) -> some View {
        content
            .padding(padded ? Theme.Spacing.xxl : 0)
            .background(Theme.Colors.surface)
            .overlay(
                RoundedRectangle(cornerRadius: Theme.Radius.card)
                    .stroke(Theme.Colors.border, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.card))
    }
}

extension View {
    func surfacePanel(padded: Bool = true) -> some View {
        modifier(SurfaceModifier(padded: padded))
    }

    func screenBackground() -> some View {
        background(Theme.Colors.background.ignoresSafeArea())
    }
}

struct PrimaryButtonStyle: ButtonStyle {
    var variant: Variant = .primary
    var compact = false

    enum Variant {
        case primary
        case secondary
        case ghost
    }

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(Theme.Fonts.label(compact ? 15 : 16, weight: .bold))
            .frame(maxWidth: compact ? nil : .infinity, minHeight: compact ? 44 : 52)
            .padding(.horizontal, compact ? 14 : 18)
            .background(background(configuration: configuration))
            .foregroundStyle(foreground)
            .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.button))
            .opacity(configuration.isPressed ? 0.75 : 1)
    }

    private func background(configuration: Configuration) -> Color {
        switch variant {
        case .primary:
            return configuration.isPressed ? Theme.Colors.primaryDark : Theme.Colors.primary
        case .secondary:
            return Theme.Colors.surfaceMuted
        case .ghost:
            return .clear
        }
    }

    private var foreground: Color {
        switch variant {
        case .primary:
            return Color("PrimaryActionText")
        case .secondary:
            return Theme.Colors.text
        case .ghost:
            return Theme.Colors.primary
        }
    }
}
