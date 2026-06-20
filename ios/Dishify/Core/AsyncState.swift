import Foundation

enum AsyncState<Value: Equatable>: Equatable {
    case idle
    case loading
    case loaded(Value)
    case failed(String)

    var isLoading: Bool {
        if case .loading = self { return true }
        return false
    }

    var value: Value? {
        if case .loaded(let value) = self { return value }
        return nil
    }

    var errorMessage: String? {
        if case .failed(let message) = self { return message }
        return nil
    }
}

enum LoadMarker: Equatable {
    case ready
}

extension APIError {
    enum Context {
        case recommend
        case preferences
        case general
    }

    func userMessage(for context: Context = .general) -> String {
        switch self {
        case .auth:
            return "Your session expired. Sign in again."
        case .validation(let message):
            return message
        case .unavailable(let detail):
            let fallback: String
            switch context {
            case .recommend:
                fallback = "The recommendation service is warming up. Make sure the backend is running and recipes are indexed."
            case .preferences:
                fallback = "Preferences service is temporarily unavailable. Try again shortly."
            case .general:
                fallback = "Service temporarily unavailable."
            }

            guard let detail, !detail.isEmpty else {
                return fallback
            }
            return "\(fallback)\n\n\(detail)"
        default:
            return localizedDescription
        }
    }
}
