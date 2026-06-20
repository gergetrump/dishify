import SwiftUI

struct ContentView: View {
    var body: some View {
        VStack(spacing: Theme.Spacing.md) {
            Image(systemName: "fork.knife")
                .font(.system(size: 48))
                .foregroundStyle(Theme.Colors.accent)

            Text("Dishify")
                .font(Theme.Typography.title)
                .foregroundStyle(Theme.Colors.textPrimary)

            Text("AI-powered recipe recommendations")
                .font(Theme.Typography.body)
                .foregroundStyle(Theme.Colors.textSecondary)
                .multilineTextAlignment(.center)
        }
        .padding(Theme.Spacing.md)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.Colors.background)
        .task {
            #if DEBUG
            await runStartupChecks()
            #endif
        }
    }

    #if DEBUG
    private func runStartupChecks() async {
        print("[Config] api=\(Config.apiBaseURL.absoluteString) keycloak=\(Config.keycloakBaseURL.absoluteString) realm=\(Config.realm) client=\(Config.iosClientID) redirect=\(Config.redirectURI)")

        let client = APIClient()
        do {
            let health = try await client.health()
            print("[APIClient] health status=\(health.status) service=\(health.service)")
        } catch {
            print("[APIClient] health failed: \(error.localizedDescription)")
        }
    }
    #endif
}

#Preview {
    ContentView()
}
