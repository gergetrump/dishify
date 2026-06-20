import Foundation

struct AuthConfig: Codable, Equatable {
    let issuer: String
    let authorizationEndpoint: String
    let tokenEndpoint: String
    let logoutEndpoint: String
    let userinfoEndpoint: String
    let jwksURI: String
    let realm: String
    let clients: Clients

    enum CodingKeys: String, CodingKey {
        case issuer
        case authorizationEndpoint = "authorization_endpoint"
        case tokenEndpoint = "token_endpoint"
        case logoutEndpoint = "logout_endpoint"
        case userinfoEndpoint = "userinfo_endpoint"
        case jwksURI = "jwks_uri"
        case realm
        case clients
    }

    struct Clients: Codable, Equatable {
        let ios: String
        let web: String
        let backend: String
        let api: String
    }
}

struct TokenResponse: Codable, Equatable {
    let accessToken: String
    let expiresIn: Int
    let refreshToken: String
    let tokenType: String
    let scope: String

    enum CodingKeys: String, CodingKey {
        case accessToken = "access_token"
        case expiresIn = "expires_in"
        case refreshToken = "refresh_token"
        case tokenType = "token_type"
        case scope
    }
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
    let message: String
}
