import Foundation

enum Config {
    private static let defaultAPIBaseURL = URL(string: "http://localhost:8000")!

    static var apiBaseURL: URL {
        url(forKey: "DishifyAPIBaseURL", default: defaultAPIBaseURL)
    }

    static let apiSession: URLSession = {
        let configuration = URLSessionConfiguration.default
        configuration.timeoutIntervalForRequest = 30
        configuration.timeoutIntervalForResource = 60
        configuration.waitsForConnectivity = false
        return URLSession(configuration: configuration)
    }()

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
