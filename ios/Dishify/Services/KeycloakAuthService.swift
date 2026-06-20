import AuthenticationServices
import CryptoKit
import Foundation
import Security
import UIKit

@MainActor
final class KeycloakAuthService: NSObject, ObservableObject {
	static let shared = KeycloakAuthService()

	@Published var isAuthenticated = false
	@Published var accessToken: String?

	private let keycloakBase = URL(string: "http://127.0.0.1:9001")!
	private let realm = "dishify"
	private let clientId = "dishify-ios"
	private let redirectURI = "dishify://callback"
	private let tokenKey = "dishify.accessToken"

	private var authSession: ASWebAuthenticationSession?
	private var codeVerifier: String?

	override private init() {
		super.init()
		accessToken = loadToken()
		isAuthenticated = accessToken != nil
		APIClient.shared.accessToken = accessToken
	}

	func login() {
		codeVerifier = Self.randomURLSafeString(length: 64)
		guard let codeVerifier,
		      let codeChallenge = Self.codeChallenge(for: codeVerifier),
		      var components = URLComponents(
		      	url: keycloakBase
		      		.appendingPathComponent("realms")
		      		.appendingPathComponent(realm)
		      		.appendingPathComponent("protocol/openid-connect/auth"),
		      	resolvingAgainstBaseURL: false
		      )
		else { return }

		components.queryItems = [
			URLQueryItem(name: "client_id", value: clientId),
			URLQueryItem(name: "redirect_uri", value: redirectURI),
			URLQueryItem(name: "response_type", value: "code"),
			URLQueryItem(name: "scope", value: "openid profile email"),
			URLQueryItem(name: "code_challenge", value: codeChallenge),
			URLQueryItem(name: "code_challenge_method", value: "S256"),
		]

		guard let authURL = components.url,
		      let callbackURL = URL(string: redirectURI)
		else { return }

		authSession = ASWebAuthenticationSession(
			url: authURL,
			callbackURLScheme: callbackURL.scheme
		) { [weak self] callback, error in
			guard let self else { return }
			if error != nil { return }
			guard let callback,
			      let code = URLComponents(url: callback, resolvingAgainstBaseURL: false)?
			      	.queryItems?
			      	.first(where: { $0.name == "code" })?
			      	.value
			else { return }
			Task { await self.exchangeCode(code, verifier: codeVerifier) }
		}
		authSession?.presentationContextProvider = self
		authSession?.prefersEphemeralWebBrowserSession = true
		authSession?.start()
	}

	func logout() {
		accessToken = nil
		isAuthenticated = false
		APIClient.shared.accessToken = nil
		deleteToken()
	}

	private func exchangeCode(_ code: String, verifier: String) async {
		guard let url = URL(
			string: "\(keycloakBase.absoluteString)/realms/\(realm)/protocol/openid-connect/token"
		) else { return }

		var request = URLRequest(url: url)
		request.httpMethod = "POST"
		request.setValue("application/x-www-form-urlencoded", forHTTPHeaderField: "Content-Type")
		let body = [
			"grant_type=authorization_code",
			"client_id=\(clientId)",
			"code=\(code)",
			"redirect_uri=\(redirectURI)",
			"code_verifier=\(verifier)",
		].joined(separator: "&")
		request.httpBody = body.data(using: .utf8)

		do {
			let (data, response) = try await URLSession.shared.data(for: request)
			guard let http = response as? HTTPURLResponse, http.statusCode == 200 else { return }
			let json = try JSONSerialization.jsonObject(with: data) as? [String: Any]
			guard let token = json?["access_token"] as? String else { return }
			accessToken = token
			isAuthenticated = true
			APIClient.shared.accessToken = token
			saveToken(token)
		} catch {
			return
		}
	}

	private func saveToken(_ token: String) {
		let data = Data(token.utf8)
		let query: [String: Any] = [
			kSecClass as String: kSecClassGenericPassword,
			kSecAttrAccount as String: tokenKey,
			kSecValueData as String: data,
		]
		SecItemDelete(query as CFDictionary)
		SecItemAdd(query as CFDictionary, nil)
	}

	private func loadToken() -> String? {
		let query: [String: Any] = [
			kSecClass as String: kSecClassGenericPassword,
			kSecAttrAccount as String: tokenKey,
			kSecReturnData as String: true,
		]
		var item: CFTypeRef?
		let status = SecItemCopyMatching(query as CFDictionary, &item)
		guard status == errSecSuccess, let data = item as? Data else { return nil }
		return String(data: data, encoding: .utf8)
	}

	private func deleteToken() {
		let query: [String: Any] = [
			kSecClass as String: kSecClassGenericPassword,
			kSecAttrAccount as String: tokenKey,
		]
		SecItemDelete(query as CFDictionary)
	}

	private static func randomURLSafeString(length: Int) -> String {
		let chars = Array("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-._~")
		return String((0 ..< length).map { _ in chars.randomElement()! })
	}

	private static func codeChallenge(for verifier: String) -> String? {
	 guard let data = verifier.data(using: .utf8) else { return nil }
	 let hash = SHA256.hash(data: data)
	 return Data(hash)
	 	.base64EncodedString()
	 	.replacingOccurrences(of: "+", with: "-")
	 	.replacingOccurrences(of: "/", with: "_")
	 	.replacingOccurrences(of: "=", with: "")
	}
}

extension KeycloakAuthService: ASWebAuthenticationPresentationContextProviding {
	func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
		let scene = UIApplication.shared.connectedScenes
			.compactMap { $0 as? UIWindowScene }
			.first { $0.activationState == .foregroundActive }
		return scene?.windows.first { $0.isKeyWindow } ?? ASPresentationAnchor()
	}
}
