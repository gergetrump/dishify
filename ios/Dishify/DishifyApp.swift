import SwiftUI

@main
struct DishifyApp: App {
	@StateObject private var auth = KeycloakAuthService.shared
	@StateObject private var api = APIClient.shared

	var body: some Scene {
		WindowGroup {
			ContentView()
				.environmentObject(auth)
				.environmentObject(api)
		}
	}
}
