import SwiftUI

struct MainTabView: View {
    @EnvironmentObject private var session: SessionStore

    var body: some View {
        TabView {
            RecommendTab(session: session)
                .tabItem {
                    Label("Recommend", systemImage: "fork.knife")
                }
                .accessibilityLabel("Recommend tab")

            PreferencesTab(session: session)
                .tabItem {
                    Label("Preferences", systemImage: "leaf")
                }
                .accessibilityLabel("Preferences tab")

            AccountView()
                .tabItem {
                    Label("Account", systemImage: "person.crop.circle")
                }
                .accessibilityLabel("Account tab")
        }
        .tint(Theme.Colors.accent)
    }
}

private struct RecommendTab: View {
    @ObservedObject var session: SessionStore
    @StateObject private var viewModel: RecommendViewModel

    init(session: SessionStore) {
        self.session = session
        _viewModel = StateObject(wrappedValue: RecommendViewModel(session: session))
    }

    var body: some View {
        RecommendView(viewModel: viewModel)
    }
}

private struct PreferencesTab: View {
    @ObservedObject var session: SessionStore
    @StateObject private var viewModel: PreferencesViewModel

    init(session: SessionStore) {
        self.session = session
        _viewModel = StateObject(wrappedValue: PreferencesViewModel(session: session))
    }

    var body: some View {
        PreferencesView(viewModel: viewModel)
    }
}

private struct AccountView: View {
    @EnvironmentObject private var session: SessionStore

    var body: some View {
        NavigationStack {
            VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
                if let profile = session.currentProfile {
                    VStack(alignment: .leading, spacing: Theme.Spacing.xs) {
                        Text(profile.username)
                            .font(Theme.Typography.largeTitle)
                            .foregroundStyle(Theme.Colors.textPrimary)

                        Text(profile.email)
                            .font(Theme.Typography.body)
                            .foregroundStyle(Theme.Colors.textSecondary)
                    }
                    .accessibilityElement(children: .combine)
                    .accessibilityLabel("Signed in as \(profile.username), \(profile.email)")
                } else {
                    Text("Signed in")
                        .font(Theme.Typography.largeTitle)
                        .foregroundStyle(Theme.Colors.textPrimary)
                }

                Button("Sign Out") {
                    session.signOut()
                }
                .font(Theme.Typography.headline)
                .foregroundStyle(Theme.Colors.error)
                .frame(maxWidth: .infinity, minHeight: Theme.Layout.minTapTarget, alignment: .leading)
                .accessibilityLabel("Sign out")
                .accessibilityHint("Ends your session and returns to the sign in screen.")

                Spacer()
            }
            .padding(Theme.Spacing.md)
            .frame(maxWidth: Theme.Layout.contentMaxWidth)
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
            .background(Theme.Colors.background)
            .navigationTitle("Account")
        }
    }
}

#Preview {
    MainTabView()
        .environmentObject(SessionStore())
}
