import SwiftUI

struct ProfilePage: View {
    @EnvironmentObject private var session: SessionStore
    @EnvironmentObject private var router: AppRouter

    @State private var error: String?
    @State private var isLoading = false

    var body: some View {
        VStack(alignment: .leading, spacing: 20) {
            Eyebrow(text: "Account")
            Text("Profile")
                .font(.system(size: 40, weight: .black))

            if let error {
                AlertBanner(text: error)
            }

            if isLoading {
                Text("Loading your profile...")
                    .foregroundStyle(Theme.Colors.muted)
            }

            VStack(spacing: 0) {
                ProfileRow(label: "Username", value: session.user?.username ?? "Not loaded")
                ProfileRow(label: "Email", value: session.user?.email ?? "Not loaded")
                ProfileRow(label: "Email verified", value: formatBoolean(session.user?.emailVerified))
            }
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Theme.Colors.border, lineWidth: 1)
            )
            .clipShape(RoundedRectangle(cornerRadius: 8))

            HStack(spacing: 10) {
                Button("Food preferences") {
                    router.go(.preferences)
                }
                .buttonStyle(PrimaryButtonStyle())
                Button("Log out") {
                    session.logout()
                    router.go(.welcome)
                }
                .buttonStyle(PrimaryButtonStyle(variant: .secondary))
            }

            Text("Password changes and account deletion are not available in the backend yet.")
                .foregroundStyle(Theme.Colors.muted)
                .padding(.top, 16)
                .overlay(Divider(), alignment: .top)
        }
        .frame(maxWidth: 440)
        .surfacePanel()
        .frame(maxWidth: .infinity)
        .task {
            await refresh()
        }
    }

    private func refresh() async {
        guard session.user == nil else { return }
        isLoading = true
        defer { isLoading = false }
        do {
            _ = try await session.loadUser()
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func formatBoolean(_ value: Bool?) -> String {
        guard let value else { return "Not loaded" }
        return value ? "Yes" : "No"
    }
}

private struct ProfileRow: View {
    let label: String
    let value: String

    var body: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text(label)
                .font(.system(size: 13, weight: .heavy))
                .foregroundStyle(Theme.Colors.muted)
            Text(value)
                .font(.system(size: 17, weight: .black))
                .foregroundStyle(Theme.Colors.text)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(Theme.Colors.surface)
        .overlay(Divider(), alignment: .bottom)
    }
}
