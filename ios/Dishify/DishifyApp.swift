import SwiftUI

@main
struct DishifyApp: App {
    @StateObject private var session = SessionStore()
    @StateObject private var router = AppRouter()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environmentObject(session)
                .environmentObject(router)
        }
    }
}
