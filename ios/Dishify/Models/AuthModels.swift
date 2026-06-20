import Foundation

struct HealthResponse: Codable, Equatable {
    let status: String
    let service: String
}

struct LoginRequest: Codable, Equatable {
    let username: String
    let password: String
}

struct RegisterRequest: Codable, Equatable {
    let username: String
    let email: String
    let password: String
    let exclusionRestrictions: [String]?

    enum CodingKeys: String, CodingKey {
        case username
        case email
        case password
        case exclusionRestrictions = "exclusion_restrictions"
    }
}

struct RegisterResponse: Codable, Equatable {
    let id: String
    let username: String
    let email: String
    let message: String?
}

struct TokenResponse: Codable, Equatable {
    let accessToken: String
    let expiresIn: Int
    let refreshToken: String?
    let tokenType: String
    let scope: String?

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case expiresIn = "expires_in"
        case refreshToken = "refresh_token"
        case tokenType = "token_type"
        case scope
    }
}
