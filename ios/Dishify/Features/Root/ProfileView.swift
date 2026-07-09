import SwiftUI

struct ProfilePage: View {
    @EnvironmentObject private var session: SessionStore
    @EnvironmentObject private var router: AppRouter

    @State private var error: String?
    @State private var isLoading = false

    var body: some View {
        VStack(spacing: 0) {
            header

            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                    DishifyBrandMark(logoSize: .compact, showWordmark: true)
                        .padding(.top, Theme.Spacing.md)

                    if let error {
                        AlertBanner(text: error)
                    }

                    if isLoading {
                        LoadingState(message: "Loading your profile...", branded: true)
                    }

                    ReadOnlyField(label: "Email", value: session.user?.email ?? "Not loaded")
                    ReadOnlyField(label: "Username", value: session.user?.username ?? "Not loaded")

                    Text("Password changes and account deletion are not available in the backend yet.")
                        .font(Theme.Fonts.body(14))
                        .foregroundStyle(Theme.Colors.muted)

                    Button("Food preferences") {
                        router.push(.preferences)
                    }
                    .buttonStyle(PrimaryButtonStyle(variant: .secondary))

                    Button("Sign out") {
                        session.logout()
                        router.resetToWelcome()
                    }
                    .buttonStyle(PrimaryButtonStyle())

                    TextLinkButton(title: "Delete account", disabled: true) {}
                        .frame(maxWidth: .infinity)
                }
                .padding(Theme.Spacing.screenPadding)
            }
        }
        .screenBackground()
        .navigationBarHidden(true)
        .task {
            await refresh()
        }
    }

    private var header: some View {
        HStack {
            Button {
                router.pop()
            } label: {
                Text("Back")
                    .font(Theme.Fonts.label(16, weight: .semibold))
                    .foregroundStyle(Theme.Colors.primary)
            }
            Spacer()
            Text("Profile")
                .font(Theme.Fonts.display(18, weight: .bold))
                .foregroundStyle(Theme.Colors.text)
            Spacer()
            Color.clear.frame(width: 36, height: 36)
        }
        .padding(.horizontal, Theme.Spacing.screenPadding)
        .padding(.vertical, Theme.Spacing.md)
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
}
