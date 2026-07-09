import SwiftUI

// MARK: - Navigation

struct ProfileToolbarButton: View {
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Image(systemName: "person.fill")
                .font(.system(size: 14, weight: .semibold))
                .foregroundStyle(Color("PrimaryActionText"))
                .frame(width: 36, height: 36)
                .background(Theme.Colors.primary)
                .clipShape(Circle())
        }
        .accessibilityLabel("Profile")
    }
}

// MARK: - Alerts & states

struct AlertBanner: View {
    enum Kind {
        case error
        case success
    }

    let text: String
    var kind: Kind = .error

    var body: some View {
        Text(text)
            .font(Theme.Fonts.label(15, weight: .semibold))
            .foregroundStyle(kind == .error ? Theme.Colors.errorText : Theme.Colors.successText)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
            .background(kind == .error ? Theme.Colors.errorBackground : Theme.Colors.successBackground)
            .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.input))
    }
}

struct LoadingState: View {
    var message = "Loading..."
    var branded = false

    var body: some View {
        VStack(spacing: Theme.Spacing.lg) {
            if branded {
                DishifyLogo(size: .icon)
            }
            HStack(spacing: Theme.Spacing.md) {
                ProgressView()
                Text(message)
                    .font(Theme.Fonts.body(15))
                    .foregroundStyle(Theme.Colors.muted)
            }
            .frame(maxWidth: .infinity, alignment: branded ? .center : .leading)
        }
        .frame(maxWidth: .infinity, alignment: branded ? .center : .leading)
    }
}

struct EmptyState: View {
    let text: String

    var body: some View {
        Text(text)
            .font(Theme.Fonts.body(15))
            .foregroundStyle(Theme.Colors.muted)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(Theme.Spacing.lg)
            .background(Theme.Colors.cardBackground)
            .overlay(
                RoundedRectangle(cornerRadius: Theme.Radius.card)
                    .stroke(Theme.Colors.border, style: StrokeStyle(lineWidth: 1, dash: [5]))
            )
    }
}

// MARK: - Forms

struct LabeledField<Content: View>: View {
    let title: String
    let hint: String?
    @ViewBuilder let content: Content

    init(_ title: String, hint: String? = nil, @ViewBuilder content: () -> Content) {
        self.title = title
        self.hint = hint
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
            HStack(spacing: 4) {
                Text(title)
                    .font(Theme.Fonts.label(14, weight: .semibold))
                    .foregroundStyle(Theme.Colors.text)
                if let hint {
                    Text(hint)
                        .font(Theme.Fonts.label(12, weight: .medium))
                        .foregroundStyle(Theme.Colors.muted)
                }
            }
            content
        }
    }
}

struct DishifyTextFieldStyle: TextFieldStyle {
    var focused = false

    func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .font(Theme.Fonts.body(16))
            .padding(.horizontal, 14)
            .frame(minHeight: 48)
            .background(Color.white)
            .overlay(
                RoundedRectangle(cornerRadius: Theme.Radius.input)
                    .stroke(focused ? Theme.Colors.primary : Theme.Colors.border, lineWidth: focused ? 2 : 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.input))
    }
}

struct ReadOnlyField: View {
    let label: String
    let value: String

    var body: some View {
        LabeledField(label) {
            Text(value)
                .font(Theme.Fonts.body(16))
                .foregroundStyle(Theme.Colors.text)
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 14)
                .frame(minHeight: 48)
                .background(Color.white)
                .overlay(
                    RoundedRectangle(cornerRadius: Theme.Radius.input)
                        .stroke(Theme.Colors.border, lineWidth: 1)
                )
                .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.input))
        }
    }
}

struct TextLinkButton: View {
    let title: String
    let action: () -> Void
    var disabled = false

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(Theme.Fonts.label(16, weight: .semibold))
                .foregroundStyle(disabled ? Theme.Colors.muted : Theme.Colors.primary)
        }
        .disabled(disabled)
    }
}

// MARK: - Chips

struct Chip: View {
    let title: String
    let selected: Bool
    var disabled = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 6) {
                if selected {
                    Image(systemName: "checkmark")
                        .font(.system(size: 11, weight: .bold))
                }
                Text(title)
                    .font(Theme.Fonts.label(14, weight: .semibold))
            }
            .textCase(.none)
            .padding(.horizontal, 13)
            .padding(.vertical, 9)
            .background(selected ? Theme.Colors.primary : Theme.Colors.surfaceMuted)
            .foregroundStyle(selected ? Color("PrimaryActionText") : Theme.Colors.text)
            .clipShape(Capsule())
        }
        .disabled(disabled)
    }
}

// MARK: - Pantry

struct IngredientCard: View {
    let name: String
    let detail: String
    let onEdit: () -> Void
    let onDelete: () -> Void

    var body: some View {
        HStack {
            VStack(alignment: .leading, spacing: 3) {
                Text(name)
                    .font(Theme.Fonts.label(16, weight: .bold))
                    .foregroundStyle(Theme.Colors.text)
                Text(detail)
                    .font(Theme.Fonts.body(14))
                    .foregroundStyle(Theme.Colors.muted)
            }
            Spacer()
            Menu {
                Button("Edit", action: onEdit)
                Button("Delete", role: .destructive, action: onDelete)
            } label: {
                Image(systemName: "ellipsis")
                    .font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(Theme.Colors.muted)
                    .frame(width: 32, height: 32)
            }
        }
        .padding(.horizontal, 14)
        .padding(.vertical, 12)
        .background(Theme.Colors.cardBackground)
        .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.card))
    }
}

// MARK: - Recipe

struct MissingBadge: View {
    var body: some View {
        Text("MISSING")
            .font(.system(size: 10, weight: .black))
            .foregroundStyle(.white)
            .padding(.horizontal, 8)
            .padding(.vertical, 4)
            .background(Theme.Colors.missing)
            .clipShape(Capsule())
    }
}

struct StepRow: View {
    let number: Int
    let text: String
    var durationMinutes: Int?
    var tip: String?

    var body: some View {
        HStack(alignment: .top, spacing: Theme.Spacing.md) {
            Text("\(number)")
                .font(Theme.Fonts.label(14, weight: .semibold))
                .foregroundStyle(Theme.Colors.text)
                .frame(width: 28, height: 28)
                .overlay(Circle().stroke(Theme.Colors.text, lineWidth: 1))
            VStack(alignment: .leading, spacing: 4) {
                Text(text)
                    .font(Theme.Fonts.body(16))
                    .foregroundStyle(Theme.Colors.text)
                if let durationMinutes {
                    Text("~\(durationMinutes) min")
                        .font(Theme.Fonts.body(14))
                        .foregroundStyle(Theme.Colors.muted)
                        .italic()
                }
                if let tip, !tip.isEmpty {
                    Text("Tip: \(tip)")
                        .font(Theme.Fonts.body(14))
                        .foregroundStyle(Theme.Colors.muted)
                }
            }
        }
    }
}

struct RecipeMetaRow: View {
    let timeMinutes: Int?
    let score: Int?

    var body: some View {
        HStack(spacing: 6) {
            if let timeMinutes {
                Text("\(timeMinutes)min")
            }
            if timeMinutes != nil, score != nil {
                Text("·")
            }
            if let score {
                Text("Score \(score)")
            }
        }
        .font(Theme.Fonts.body(14))
        .foregroundStyle(Theme.Colors.muted)
    }
}

struct MetaPill: View {
    let text: String

    var body: some View {
        Text(text)
            .font(Theme.Fonts.label(13, weight: .semibold))
            .foregroundStyle(Theme.Colors.muted)
    }
}

// MARK: - Layout

struct FlowLayout<Data: RandomAccessCollection, Content: View>: View where Data.Element: Hashable {
    let data: Data
    let spacing: CGFloat
    let content: (Data.Element) -> Content

    init(_ data: Data, spacing: CGFloat = 10, @ViewBuilder content: @escaping (Data.Element) -> Content) {
        self.data = data
        self.spacing = spacing
        self.content = content
    }

    var body: some View {
        LazyVGrid(columns: [GridItem(.adaptive(minimum: 120), spacing: spacing)], spacing: spacing) {
            ForEach(Array(data), id: \.self) { item in
                content(item)
            }
        }
    }
}

// MARK: - Brand

struct DishifyLogo: View {
    enum Size {
        case icon
        case compact
        case hero

        var dimension: CGFloat {
            switch self {
            case .icon: 36
            case .compact: 120
            case .hero: 240
            }
        }
    }

    var size: Size = .hero

    var body: some View {
        Image("WelcomeBowl")
            .resizable()
            .scaledToFit()
            .frame(width: size.dimension, height: size.dimension)
            .accessibilityLabel("Dishify")
    }
}

struct DishifyBrandMark: View {
    var logoSize: DishifyLogo.Size = .compact
    var showWordmark = true

    var body: some View {
        VStack(spacing: Theme.Spacing.md) {
            DishifyLogo(size: logoSize)
            if showWordmark {
                Text("Dishify")
                    .font(Theme.Fonts.display(28, weight: .bold))
                    .foregroundStyle(Theme.Colors.text)
            }
        }
        .frame(maxWidth: .infinity)
    }
}

struct BrandedEmptyState: View {
    let text: String

    var body: some View {
        VStack(spacing: Theme.Spacing.lg) {
            DishifyLogo(size: .compact)
                .opacity(0.9)
            EmptyState(text: text)
        }
    }
}

struct WelcomeBowlIllustration: View {
    var body: some View {
        DishifyLogo(size: .hero)
    }
}

// MARK: - Legacy aliases

typealias FieldLabel = LabeledField
typealias ChipButton = Chip
typealias WebTextFieldStyle = DishifyTextFieldStyle

struct Eyebrow: View {
    let text: String

    var body: some View {
        Text(text.uppercased())
            .font(Theme.Fonts.label(12, weight: .bold))
            .tracking(1)
            .foregroundStyle(Theme.Colors.primaryDark)
    }
}
