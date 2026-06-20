import Foundation

enum Config {
    private static let defaultAPIBaseURL = URL(string: "http://localhost:8000")!
    private static let defaultKeycloakBaseURL = URL(string: "http://localhost:9001")!
    private static let defaultRealm = "dishify"
    private static let defaultIOSClientID = "dishify-ios"
    private static let defaultRedirectURI = "dishify://callback"

    /// Gateway base URL for `/health`, `/recommend`, `/auth/*`, `/me/*`.
    static var apiBaseURL: URL {
        url(forKey: "DishifyAPIBaseURL", default: defaultAPIBaseURL)
    }

    /// Keycloak base URL fallback when live OIDC endpoints are unavailable.
    static var keycloakBaseURL: URL {
        url(forKey: "DishifyKeycloakBaseURL", default: defaultKeycloakBaseURL)
    }

    /// Max seconds to wait for a response to start arriving before timing out.
    static let requestTimeout: TimeInterval = 30

    /// Max seconds for a full request (incl. body) to complete before timing out.
    /// Bounds worst-case "infinite spinner" waits when the backend hangs.
    static let resourceTimeout: TimeInterval = 60

    /// Shared, timeout-bounded session used by `APIClient`.
    /// `URLSession.shared` defaults to a 7-day resource timeout, which is why a
    /// hung backend can spin forever; this caps it.
    static let apiSession: URLSession = {
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = requestTimeout
        configuration.timeoutIntervalForResource = resourceTimeout
        configuration.waitsForConnectivity = false
        return URLSession(configuration: configuration)
    }()

    /// Keycloak realm name.
    static var realm: String {
        string(forKey: "DishifyRealm", default: defaultRealm)
    }

    /// Public PKCE client ID provisioned for this app.
    static var iosClientID: String {
        string(forKey: "DishifyIOSClientID", default: defaultIOSClientID)
    }

    /// OAuth redirect URI registered with Keycloak.
    static var redirectURI: String {
        string(forKey: "DishifyRedirectURI", default: defaultRedirectURI)
    }

    /// Active build flavor for logging and diagnostics.
    static var buildFlavor: String {
        #if STAGING
        return "Staging"
        #elseif DEBUG
        return "Debug"
        #else
        return "Release"
        #endif
    }

    private static func string(forKey key: String, default defaultValue: String) -> String {
        guard let value = Bundle.main.object(forInfoDictionaryKey: key) as? String,
              !value.isEmpty,
              !value.hasPrefix("$(") else {
            return defaultValue
        }
        return value
    }

    private static func url(forKey key: String, default defaultValue: URL) -> URL {
        let raw = string(forKey: key, default: defaultValue.absoluteString)
        return URL(string: raw) ?? defaultValue
    }
}
