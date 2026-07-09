import Foundation

enum InputValidation {
    static let maxTextLength = 512

    enum Failure: Equatable {
        case tooLong(max: Int)
        case controlCharacters
    }

    static func validate(_ value: String) -> Failure? {
        if value.count > maxTextLength {
            return .tooLong(max: maxTextLength)
        }
        if value.unicodeScalars.contains(where: { CharacterSet.controlCharacters.contains($0) }) {
            return .controlCharacters
        }
        return nil
    }

    static func message(for failure: Failure) -> String {
        switch failure {
        case .tooLong(let max):
            return "Text must be \(max) characters or fewer."
        case .controlCharacters:
            return "Text must not contain control characters."
        }
    }
}
