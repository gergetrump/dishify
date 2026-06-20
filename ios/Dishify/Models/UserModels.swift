import Foundation

struct UserProfile: Codable, Equatable {
    let id: String
    let username: String
    let email: String
    let emailVerified: Bool
    let firstName: String
    let lastName: String

    enum CodingKeys: String, CodingKey {
        case id
        case username
        case email
        case emailVerified = "email_verified"
        case firstName = "first_name"
        case lastName = "last_name"
    }
}

struct UserPreferences: Codable, Equatable {
    let exclusionRestrictions: [String]

    enum CodingKeys: String, CodingKey {
        case exclusionRestrictions = "exclusion_restrictions"
    }
}

struct PreferencesUpdateRequest: Codable, Equatable {
    let exclusionRestrictions: [String]?

    enum CodingKeys: String, CodingKey {
        case exclusionRestrictions = "exclusion_restrictions"
    }
}
