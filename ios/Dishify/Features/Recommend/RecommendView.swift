import SwiftUI

struct CookPage: View {
    @EnvironmentObject private var router: AppRouter

    @State private var items = PantryStore.load()
    @State private var editingID: String?
    @State private var name = ""
    @State private var quantity = ""
    @State private var unit = ""
    @State private var query = ""
    @State private var topK = 5
    @State private var error: String?
    @State private var isSubmitting = false

    private let api = APIClient()

    var body: some View {
        VStack(spacing: 24) {
            VStack(alignment: .leading, spacing: 16) {
                Eyebrow(text: "What is available today?")
                Text("Your next meal is already in your kitchen.")
                    .font(.system(size: 48, weight: .black))
                    .foregroundStyle(Theme.Colors.text)
                Text("Add pantry items, describe what sounds good, and Dishify will recommend recipes that fit.")
                    .font(.system(size: 17))
                    .lineSpacing(6)
                    .foregroundStyle(Theme.Colors.muted)
                FlowLayout(["quick high-protein dinner", "cozy vegetarian pasta", "spicy lunch with eggs"], spacing: 10) { prompt in
                    Text(prompt)
                        .font(.system(size: 14, weight: .heavy))
                        .foregroundStyle(Theme.Colors.primaryDark)
                        .padding(.horizontal, 12)
                        .padding(.vertical, 9)
                        .background(Color(red: 1, green: 0.945, blue: 0.918))
                        .clipShape(Capsule())
                }
            }
            .surfacePanel()

            VStack(alignment: .leading, spacing: 22) {
                pantryForm
                pantryList
                vibeForm
            }
            .surfacePanel()
        }
        .onChange(of: items) { updatedItems in
            PantryStore.save(updatedItems)
        }
    }

    private var pantryForm: some View {
        VStack(alignment: .leading, spacing: 12) {
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Eyebrow(text: "Pantry")
                    Text("Add ingredients")
                        .font(.system(size: 20, weight: .black))
                }
                Spacer()
                if !items.isEmpty {
                    Button("Clear all") {
                        items = []
                        resetForm()
                    }
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(Color(red: 0.812, green: 0.180, blue: 0.094))
                }
            }

            FieldLabel("Ingredient") {
                TextField("Eggs", text: $name)
                    .textFieldStyle(WebTextFieldStyle())
            }
            HStack(spacing: 12) {
                FieldLabel("Quantity") {
                    TextField("2", text: $quantity)
                        .keyboardType(.decimalPad)
                        .textFieldStyle(WebTextFieldStyle())
                }
                FieldLabel("Unit") {
                    TextField("pieces", text: $unit)
                        .textFieldStyle(WebTextFieldStyle())
                }
            }
            HStack(spacing: 10) {
                Button(editingID == nil ? "Add ingredient" : "Save ingredient") {
                    saveIngredient()
                }
                .buttonStyle(PrimaryButtonStyle(variant: .secondary))
                if editingID != nil {
                    Button("Cancel") { resetForm() }
                        .buttonStyle(PrimaryButtonStyle(variant: .ghost))
                }
            }
        }
    }

    private var pantryList: some View {
        VStack(spacing: 10) {
            if items.isEmpty {
                Text("No pantry ingredients yet.")
                    .font(.system(size: 15))
                    .foregroundStyle(Theme.Colors.muted)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(16)
                    .background(Color(red: 0.980, green: 0.969, blue: 0.949))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(Theme.Colors.border, style: StrokeStyle(lineWidth: 1, dash: [5]))
                    )
            } else {
                ForEach(items) { item in
                    HStack {
                        VStack(alignment: .leading, spacing: 3) {
                            Text(item.name)
                                .font(.system(size: 16, weight: .black))
                                .foregroundStyle(Theme.Colors.green)
                            Text(item.rawText)
                                .font(.system(size: 14))
                                .foregroundStyle(Theme.Colors.muted)
                        }
                        Spacer()
                        Button("Edit") { edit(item) }
                            .font(.system(size: 14, weight: .heavy))
                            .foregroundStyle(Theme.Colors.primaryDark)
                        Button("Delete") { delete(item) }
                            .font(.system(size: 14, weight: .heavy))
                            .foregroundStyle(Theme.Colors.primaryDark)
                    }
                    .padding(.horizontal, 14)
                    .padding(.vertical, 12)
                    .background(Color(red: 0.980, green: 0.969, blue: 0.949))
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(Theme.Colors.border, lineWidth: 1)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 8))
                }
            }
        }
    }

    private var vibeForm: some View {
        VStack(alignment: .leading, spacing: 14) {
            Divider()
            HStack(alignment: .top) {
                VStack(alignment: .leading, spacing: 4) {
                    Eyebrow(text: "Vibe check")
                    Text("What sounds good?")
                        .font(.system(size: 20, weight: .black))
                }
                Spacer()
                Picker("Results", selection: $topK) {
                    Text("3").tag(3)
                    Text("5").tag(5)
                    Text("10").tag(10)
                }
                .pickerStyle(.segmented)
                .frame(width: 150)
            }

            if let error {
                AlertBanner(text: error)
            }

            FieldLabel("Eating vibe", hint: "optional") {
                TextEditor(text: $query)
                    .frame(minHeight: 150)
                    .padding(10)
                    .background(.white)
                    .overlay(
                        RoundedRectangle(cornerRadius: 8)
                            .stroke(Theme.Colors.border, lineWidth: 1)
                    )
                    .clipShape(RoundedRectangle(cornerRadius: 8))
            }

            Button(isSubmitting ? "Finding recipes..." : "Show recipes") {
                Task { await recommend() }
            }
            .buttonStyle(PrimaryButtonStyle())
            .disabled(isSubmitting)
        }
    }

    private func saveIngredient() {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        let parsedQuantity = Double(quantity.trimmingCharacters(in: .whitespacesAndNewlines))
        let next = PantryStore.make(name: trimmed, quantity: parsedQuantity, unit: unit)

        if let editingID {
            items = items.map { $0.id == editingID ? ParsedIngredient(id: editingID, name: next.name, quantity: next.quantity, unit: next.unit, rawText: next.rawText) : $0 }
        } else {
            items.append(next)
        }
        resetForm()
    }

    private func edit(_ item: ParsedIngredient) {
        editingID = item.id
        name = item.name
        quantity = item.quantity.map { String(format: "%g", $0) } ?? ""
        unit = item.unit ?? ""
    }

    private func delete(_ item: ParsedIngredient) {
        items.removeAll { $0.id == item.id }
        if editingID == item.id { resetForm() }
    }

    private func resetForm() {
        editingID = nil
        name = ""
        quantity = ""
        unit = ""
    }

    private func recommend() async {
        error = nil
        isSubmitting = true
        defer { isSubmitting = false }

        let resolvedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? defaultQueryFromPantry()
            : query.trimmingCharacters(in: .whitespacesAndNewlines)
        let request = RecommendRequest(
            query: resolvedQuery,
            topK: topK,
            availableIngredients: items.map { ParsedIngredient(id: nil, name: $0.name, quantity: $0.quantity, unit: $0.unit, rawText: $0.rawText) },
            exclusionRestrictions: nil
        )

        do {
            let response = try await api.recommend(request)
            RecommendationStore.save(RecommendationSession(request: request, response: response))
            router.go(.results)
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func defaultQueryFromPantry() -> String {
        if items.isEmpty { return "easy dinner" }
        return "recipe using " + items.map(\.name).joined(separator: ", ")
    }
}
