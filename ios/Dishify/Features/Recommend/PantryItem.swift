import Foundation

struct PantryItem: Identifiable, Equatable {
    let id: UUID
    var rawText: String
    var quantityText: String
    var unit: String

    init(
        id: UUID = UUID(),
        rawText: String = "",
        quantityText: String = "",
        unit: String = ""
    ) {
        self.id = id
        self.rawText = rawText
        self.quantityText = quantityText
        self.unit = unit
    }

    init(parsedIngredient: ParsedIngredient) {
        id = UUID()
        rawText = parsedIngredient.rawText
        quantityText = parsedIngredient.quantity.map(Self.formatQuantity) ?? ""
        unit = parsedIngredient.unit ?? ""
    }

    func toParsedIngredient() -> ParsedIngredient? {
        let trimmedRawText = rawText.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedRawText.isEmpty else {
            return nil
        }

        let trimmedUnit = unit.trimmingCharacters(in: .whitespacesAndNewlines)
        let trimmedQuantity = quantityText.trimmingCharacters(in: .whitespacesAndNewlines)

        let quantity: Double?
        if trimmedQuantity.isEmpty {
            quantity = nil
        } else {
            quantity = Double(trimmedQuantity)
        }

        return ParsedIngredient(
            name: trimmedRawText,
            quantity: quantity,
            unit: trimmedUnit.isEmpty ? nil : trimmedUnit,
            rawText: trimmedRawText
        )
    }

    static func parsedIngredients(from items: [PantryItem]) -> [ParsedIngredient] {
        items.compactMap { $0.toParsedIngredient() }
    }

    static func items(from ingredients: [ParsedIngredient]) -> [PantryItem] {
        ingredients.map { PantryItem(parsedIngredient: $0) }
    }

    private static func formatQuantity(_ value: Double) -> String {
        if value.rounded() == value {
            return String(Int(value))
        }
        return String(value)
    }
}
