import XCTest
@testable import Dishify

final class AuthServiceTests: XCTestCase {
    func testPKCEChallengeIsDeterministic() {
        let verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        let challenge = PKCEGenerator.codeChallenge(for: verifier)
        XCTAssertEqual(challenge, "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM")
        XCTAssertEqual(challenge, PKCEGenerator.codeChallenge(for: verifier))
    }

    func testGeneratedVerifierUsesAllowedCharacters() {
        let verifier = PKCEGenerator.codeVerifier()
        XCTAssertGreaterThanOrEqual(verifier.count, 43)
        XCTAssertTrue(verifier.allSatisfy { $0.isLetter || $0.isNumber || "-._~".contains($0) })
    }

    func testChallengeIsURLSafeBase64() {
        let challenge = PKCEGenerator.codeChallenge(for: PKCEGenerator.codeVerifier())
        XCTAssertFalse(challenge.contains("+"))
        XCTAssertFalse(challenge.contains("/"))
        XCTAssertFalse(challenge.contains("="))
    }

    func testKeychainStoreRoundTrip() throws {
        let keychain = KeychainStore(service: "com.dishify.app.tests", account: UUID().uuidString)
        defer { keychain.delete() }

        let tokens = StoredTokens(
            accessToken: "access",
            refreshToken: "refresh",
            expiresIn: 300
        )

        try keychain.save(tokens)
        let loaded = keychain.load()

        XCTAssertEqual(loaded, tokens)
    }

    func testKeychainDeleteRemovesStoredTokens() throws {
        let keychain = KeychainStore(service: "com.dishify.app.tests", account: UUID().uuidString)
        let tokens = StoredTokens(
            accessToken: "access",
            refreshToken: "refresh",
            expiresIn: 300
        )

        try keychain.save(tokens)
        keychain.delete()

        XCTAssertNil(keychain.load())
    }

    func testStoredTokensMarksExpiringSoonWithinBuffer() {
        let tokens = StoredTokens(
            accessToken: "access",
            refreshToken: "refresh",
            expiresIn: 20
        )

        XCTAssertTrue(tokens.isExpiringSoon)
    }

    func testStoredTokensNotExpiringSoonWhenFresh() {
        let tokens = StoredTokens(
            accessToken: "access",
            refreshToken: "refresh",
            expiresIn: 300
        )

        XCTAssertFalse(tokens.isExpiringSoon)
    }

    func testStoredTokensInitFromTokenResponseHonorsExpiresIn() {
        let response = TokenResponse(
            accessToken: "access",
            expiresIn: 300,
            refreshToken: "refresh",
            tokenType: "Bearer",
            scope: "openid profile email"
        )

        let tokens = StoredTokens(response: response)

        XCTAssertEqual(tokens.accessToken, "access")
        XCTAssertEqual(tokens.refreshToken, "refresh")
        XCTAssertFalse(tokens.isExpiringSoon)
    }
}
