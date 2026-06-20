import SwiftUI

struct RootView: View {
    @EnvironmentObject private var session: SessionStore
    @EnvironmentObject private var router: AppRouter

    var body: some View {
        ScrollView {
            VStack(spacing: 0) {
                AppHeader()
                pageView
                    .padding(24)
                    .frame(maxWidth: 1120)
                    .frame(maxWidth: .infinity)
            }
        }
        .background(Theme.Colors.background.ignoresSafeArea())
        .onChange(of: session.isAuthenticated) { isAuthenticated in
            if !isAuthenticated {
                router.go(.welcome)
            }
        }
    }

    @ViewBuilder
    private var pageView: some View {
        switch router.page {
        case .welcome:
            WelcomePage()
        case .login:
            LoginPage()
        case .register:
            RegisterPage()
        case .cook:
            CookPage()
        case .preferences:
            RequireAuthView { PreferencesPage() }
        case .results:
            RequireAuthView { ResultsPage() }
        case .recipe(let id):
            RequireAuthView { RecipeDetailPage(recipeID: id) }
        case .profile:
            RequireAuthView { ProfilePage() }
        }
    }
}

private struct RequireAuthView<Content: View>: View {
    @EnvironmentObject private var session: SessionStore
    @EnvironmentObject private var router: AppRouter
    @ViewBuilder let content: Content

    var body: some View {
        Group {
            if session.isAuthenticated {
                content
            } else {
                LoginPage()
                    .onAppear {
                        router.go(.login)
                    }
            }
        }
    }
}

private struct AppHeader: View {
    @EnvironmentObject private var session: SessionStore
    @EnvironmentObject private var router: AppRouter

    var body: some View {
        HStack(alignment: .center, spacing: 24) {
            Button {
                router.go(.cook)
            } label: {
                HStack(spacing: 10) {
                    Text("D")
                        .font(.system(size: 17, weight: .black))
                        .foregroundStyle(.white)
                        .frame(width: 34, height: 34)
                        .background(Theme.Colors.green)
                        .clipShape(RoundedRectangle(cornerRadius: 12))
                    Text("Dishify")
                        .font(.system(size: 18, weight: .bold))
                        .foregroundStyle(Theme.Colors.text)
                }
            }

            Spacer()

            HStack(spacing: 16) {
                HeaderLink("Cook", page: .cook)
                if session.isAuthenticated {
                    HeaderLink("Preferences", page: .preferences)
                    HeaderLink("Profile", page: .profile)
                    Button("Log out") {
                        session.logout()
                        router.go(.welcome)
                    }
                    .font(.system(size: 15, weight: .bold))
                    .foregroundStyle(Theme.Colors.primaryDark)
                } else {
                    HeaderLink("Log in", page: .login)
                    HeaderLink("Sign up", page: .register)
                }
            }
        }
        .padding(24)
        .frame(maxWidth: 1120)
        .frame(maxWidth: .infinity)
    }
}

private struct HeaderLink: View {
    @EnvironmentObject private var router: AppRouter
    let title: String
    let page: AppRouter.Page

    init(_ title: String, page: AppRouter.Page) {
        self.title = title
        self.page = page
    }

    var body: some View {
        Button(title) {
            router.go(page)
        }
        .font(.system(size: 15, weight: .bold))
        .foregroundStyle(Theme.Colors.primaryDark)
    }
}
