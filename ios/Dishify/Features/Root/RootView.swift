import SwiftUI

struct RootView: View {
    @EnvironmentObject private var session: SessionStore
    @EnvironmentObject private var router: AppRouter

    var body: some View {
        NavigationStack(path: $router.path) {
            rootContent
                .navigationDestination(for: AppRouter.Page.self, destination: destinationView)
        }
        .screenBackground()
        .onChange(of: session.isAuthenticated) { isAuthenticated in
            if !isAuthenticated {
                router.resetToWelcome()
            } else if router.page == .welcome || router.page == .login || router.page == .register {
                router.resetToCook()
            }
        }
    }

    @ViewBuilder
    private var rootContent: some View {
        switch router.page {
        case .welcome:
            WelcomePage()
        case .login:
            LoginPage()
        case .register:
            RegisterPage()
        case .cook:
            RequireAuthView { PantryPage() }
        case .vibe, .results, .recipe, .profile, .preferences:
            RequireAuthView { PantryPage() }
        }
    }

    @ViewBuilder
    private func destinationView(for page: AppRouter.Page) -> some View {
        switch page {
        case .vibe:
            RequireAuthView { VibePage() }
        case .results:
            RequireAuthView { ResultsPage() }
        case .recipe(let id):
            RequireAuthView { RecipeDetailPage(recipeID: id) }
        case .profile:
            RequireAuthView { ProfilePage() }
        case .preferences:
            RequireAuthView { PreferencesPage() }
        default:
            EmptyView()
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
