import SwiftUI

struct Eyebrow: View {
    let text: String

    var body: some View {
        Text(text.uppercased())
            .font(.system(size: 12, weight: .black))
            .tracking(1)
            .foregroundStyle(Theme.Colors.primaryDark)
    }
}

struct AlertBanner: View {
    enum Kind {
        case error
        case success
    }

    let text: String
    var kind: Kind = .error

    var body: some View {
        Text(text)
            .font(.system(size: 15, weight: .heavy))
            .foregroundStyle(kind == .error ? Theme.Colors.errorText : Theme.Colors.successText)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 14)
            .padding(.vertical, 12)
            .background(kind == .error ? Theme.Colors.errorBackground : Theme.Colors.successBackground)
            .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}

struct FieldLabel<Content: View>: View {
    let title: String
    let hint: String?
    @ViewBuilder let content: Content

    init(_ title: String, hint: String? = nil, @ViewBuilder content: () -> Content) {
        self.title = title
        self.hint = hint
        self.content = content()
    }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            HStack(spacing: 4) {
                Text(title)
                    .font(.system(size: 15, weight: .heavy))
                    .foregroundStyle(Theme.Colors.text)
                if let hint {
                    Text(hint)
                        .font(.system(size: 12, weight: .heavy))
                        .foregroundStyle(Theme.Colors.muted)
                }
            }
            content
        }
    }
}

struct WebTextFieldStyle: TextFieldStyle {
    func _body(configuration: TextField<Self._Label>) -> some View {
        configuration
            .padding(.horizontal, 14)
            .frame(minHeight: 46)
            .background(.white)
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Theme.Colors.border, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}

struct ChipButton: View {
    let title: String
    let selected: Bool
    var disabled = false
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            Text(title)
                .font(.system(size: 14, weight: .heavy))
                .textCase(.none)
                .padding(.horizontal, 13)
                .padding(.vertical, 9)
                .background(selected ? Theme.Colors.primary : Theme.Colors.surfaceMuted)
                .foregroundStyle(selected ? .white : Theme.Colors.text)
                .clipShape(Capsule())
        }
        .disabled(disabled)
    }
}

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
