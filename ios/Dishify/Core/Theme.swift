import SwiftUI

enum Theme {
    enum Colors {
        static let background = Color(red: 0.965, green: 0.949, blue: 0.925)
        static let surface = Color(red: 1.0, green: 0.992, blue: 0.976)
        static let surfaceMuted = Color(red: 0.945, green: 0.925, blue: 0.902)
        static let text = Color(red: 0.141, green: 0.137, blue: 0.129)
        static let muted = Color(red: 0.408, green: 0.384, blue: 0.357)
        static let primary = Color(red: 0.957, green: 0.353, blue: 0.176)
        static let primaryDark = Color(red: 0.847, green: 0.263, blue: 0.110)
        static let green = Color(red: 0.184, green: 0.420, blue: 0.278)
        static let border = Color(red: 0.894, green: 0.867, blue: 0.831)
        static let errorBackground = Color(red: 1.0, green: 0.898, blue: 0.875)
        static let errorText = Color(red: 0.616, green: 0.165, blue: 0.067)
        static let successBackground = Color(red: 0.898, green: 0.957, blue: 0.914)
        static let successText = Color(red: 0.137, green: 0.345, blue: 0.227)
    }

    enum Spacing {
        static let xs: CGFloat = 4
        static let sm: CGFloat = 8
        static let md: CGFloat = 12
        static let lg: CGFloat = 16
        static let xl: CGFloat = 24
        static let xxl: CGFloat = 28
    }
}

struct SurfaceModifier: ViewModifier {
    func body(content: Content) -> some View {
        content
            .padding(28)
            .background(Theme.Colors.surface)
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Theme.Colors.border, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 8))
            .shadow(color: Color.black.opacity(0.08), radius: 24, x: 0, y: 12)
    }
}

extension View {
    func surfacePanel() -> some View {
        modifier(SurfaceModifier())
    }
}

struct PrimaryButtonStyle: ButtonStyle {
    var variant: Variant = .primary

    enum Variant {
        case primary
        case secondary
        case ghost
    }

    func makeBody(configuration: Configuration) -> some View {
        configuration.label
            .font(.system(size: 16, weight: .black))
            .frame(maxWidth: .infinity, minHeight: 48)
            .padding(.horizontal, 18)
            .background(background(configuration: configuration))
            .foregroundStyle(foreground)
            .clipShape(RoundedRectangle(cornerRadius: 8))
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
            return .white
        case .secondary:
            return Theme.Colors.text
        case .ghost:
            return Theme.Colors.primaryDark
        }
    }
}
