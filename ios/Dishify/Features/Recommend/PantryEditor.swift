import SwiftUI

struct PantryEditor: View {
    @Binding var ingredients: [ParsedIngredient]
    @State private var rows: [PantryItem] = []
    @State private var syncTask: Task<Void, Never>?

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
            SectionHeader(
                title: "Pantry",
                subtitle: "Add ingredients you have on hand. Quantity and unit are optional."
            )

            if rows.isEmpty {
                Text("No ingredients added yet.")
                    .font(Theme.Typography.body)
                    .foregroundStyle(Theme.Colors.textSecondary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.vertical, Theme.Spacing.sm)
                    .accessibilityLabel("No ingredients added yet.")
            } else {
                ForEach($rows) { $row in
                    PantryItemRow(row: $row, onRemove: {
                        removeRow(row.id)
                    })
                }
            }

            Button(action: addRow) {
                Label("Add Ingredient", systemImage: "plus.circle.fill")
                    .font(Theme.Typography.body)
            }
            .frame(minHeight: Theme.Layout.minTapTarget, alignment: .leading)
            .foregroundStyle(Theme.Colors.accent)
            .accessibilityLabel("Add ingredient")
            .accessibilityHint("Adds another pantry item row.")
        }
        .onAppear(perform: loadRowsIfNeeded)
        .onChange(of: rows) { _ in
            scheduleSyncIngredients()
        }
        .onDisappear {
            syncTask?.cancel()
            syncIngredients()
        }
    }

    private func loadRowsIfNeeded() {
        guard rows.isEmpty else { return }
        rows = PantryItem.items(from: ingredients)
        if rows.isEmpty {
            rows = [PantryItem()]
        }
    }

    private func addRow() {
        rows.append(PantryItem())
    }

    private func removeRow(_ id: UUID) {
        rows.removeAll { $0.id == id }
        if rows.isEmpty {
            rows = [PantryItem()]
        }
    }

    private func syncIngredients() {
        ingredients = PantryItem.parsedIngredients(from: rows)
    }

    private func scheduleSyncIngredients() {
        syncTask?.cancel()
        syncTask = Task {
            try? await Task.sleep(for: .milliseconds(300))
            guard !Task.isCancelled else { return }
            syncIngredients()
        }
    }
}

private struct PantryItemRow: View {
    @Binding var row: PantryItem
    let onRemove: () -> Void

    var body: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
            HStack(alignment: .top, spacing: Theme.Spacing.sm) {
                LabeledFormField(label: "Ingredient") {
                    TextField("e.g. penne or tomato", text: $row.rawText)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .themedField()
                        .accessibilityLabel("Ingredient name")
                }

                Button(action: onRemove) {
                    Image(systemName: "minus.circle.fill")
                        .foregroundStyle(Theme.Colors.error)
                }
                .frame(minWidth: Theme.Layout.minTapTarget, minHeight: Theme.Layout.minTapTarget)
                .accessibilityLabel("Remove ingredient")
            }

            HStack(spacing: Theme.Spacing.sm) {
                LabeledFormField(label: "Quantity") {
                    TextField("Optional", text: $row.quantityText)
                        .keyboardType(.decimalPad)
                        .themedField()
                        .accessibilityLabel("Quantity")
                }

                LabeledFormField(label: "Unit") {
                    TextField("e.g. oz", text: $row.unit)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .themedField()
                        .accessibilityLabel("Unit")
                }
            }
        }
        .padding(Theme.Spacing.sm)
        .background(Theme.Colors.background)
        .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.sm))
        .overlay(
            RoundedRectangle(cornerRadius: Theme.Radius.sm)
                .stroke(Theme.Colors.border.opacity(0.6), lineWidth: 1)
        )
    }
}

#Preview {
    struct PreviewWrapper: View {
        @State private var ingredients: [ParsedIngredient] = []

        var body: some View {
            ScrollView {
                PantryEditor(ingredients: $ingredients)
                    .padding()
                    .surfaceCard()
            }
            .background(Theme.Colors.background)
        }
    }

    return PreviewWrapper()
}
