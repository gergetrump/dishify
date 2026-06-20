import Foundation

enum APIError: Error, LocalizedError {
    case unauthorized
    case validation(String)
    case serverUnavailable(detail: String? = nil)
    case http(status: Int, body: String)
    case decoding(Error)
    case transport(Error)

    var errorDescription: String? {
        switch self {
        case .unauthorized:
            return "Authentication required."
        case .validation(let message):
            return message
        case .serverUnavailable(let detail):
            if let detail, !detail.isEmpty {
                return detail
            }
            return "Service temporarily unavailable."
        case .http(let status, let body):
            return "Request failed (\(status)): \(body)"
        case .decoding(let error):
            return "Failed to decode response: \(error.localizedDescription)"
        case .transport(let error):
            return error.localizedDescription
        }
    }

    /// Backend `detail`/`message` string, when one was returned in the body.
    var serverDetail: String? {
        if case .serverUnavailable(let detail) = self {
            return detail
        }
        return nil
    }

    static func fromResponse(status: Int, body: String) -> APIError {
        switch status {
        case 401:
            return .unauthorized
        case 422:
            return .validation(Self.detailMessage(from: body) ?? "Validation failed.")
        case 503:
            return .serverUnavailable(detail: Self.detailMessage(from: body))
        default:
            return .http(status: status, body: body)
        }
    }

    /// Extracts a human-readable message from a FastAPI-style error body.
    /// Handles `{"detail": "..."}`, `{"message": "..."}`, and
    /// `{"detail": [{"msg": "..."}]}` (422 validation) shapes.
    static func detailMessage(from body: String) -> String? {
        guard let data = body.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) else {
            return body.isEmpty ? nil : body
        }

        if let object = json as? [String: Any], let message = object["detail"] as? String {
            return message
        }

        if let object = json as? [String: Any], let message = object["message"] as? String {
            return message
        }

        if let object = json as? [String: Any], let detail = object["detail"] as? [[String: Any]],
           let first = detail.first, let message = first["msg"] as? String {
            return message
        }

        return body.isEmpty ? nil : body
    }
}
