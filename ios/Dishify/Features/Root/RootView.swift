import SwiftUI

struct RootView: View {
    @EnvironmentObject private var session: SessionStore

    var body: some View {
        Group {
            switch session.state {
            case .unknown:
                LoadingStateView(message: "Loading Dishify…")
            case .signedOut:
                AuthView()
            case .signedIn:
                MainTabView()
            }
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(Theme.Colors.background)
        .task {
            await session.bootstrap()
        }
    }
}

#Preview {
    RootView()
        .environmentObject(SessionStore())
}
