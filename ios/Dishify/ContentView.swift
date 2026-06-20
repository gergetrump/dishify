import SwiftUI

struct ContentView: View {
	@EnvironmentObject private var auth: KeycloakAuthService

	var body: some View {
		NavigationStack {
			Group {
				if auth.isAuthenticated {
					RecommendView()
				} else {
					LoginView()
				}
			}
			.navigationTitle("Dishify")
		}
	}
}

struct LoginView: View {
	@EnvironmentObject private var auth: KeycloakAuthService

	var body: some View {
		VStack(spacing: 16) {
			Text("Sign in to get recipe recommendations based on what you have.")
				.multilineTextAlignment(.center)
				.foregroundStyle(.secondary)
			Button("Sign in with Keycloak") {
				auth.login()
			}
			.buttonStyle(.borderedProminent)
		}
		.padding()
	}
}

#Preview {
	ContentView()
		.environmentObject(KeycloakAuthService.shared)
		.environmentObject(APIClient.shared)
}
