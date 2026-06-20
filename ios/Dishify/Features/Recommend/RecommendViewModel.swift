import SwiftUI

struct ResultsPage: View {
    @EnvironmentObject private var router: AppRouter

    @State private var session = RecommendationStore.load()
    @State private var error: String?
    @State private var isRetrying = false

    private let api = APIClient()

    var body: some View {
        if let session {
            VStack(alignment: .leading, spacing: 24) {
                HStack(alignment: .top) {
                    VStack(alignment: .leading, spacing: 6) {
                        Eyebrow(text: "Recipe suggestions")
                        Text("Best matches")
                            .font(.system(size: 40, weight: .black))
                            .foregroundStyle(Theme.Colors.text)
                        Text("For: \(session.request.query)")
                            .foregroundStyle(Theme.Colors.muted)
                    }
                    Spacer()
                    Button(isRetrying ? "Retrying..." : "Retry") {
                        Task { await retry() }
                    }
                    .buttonStyle(PrimaryButtonStyle(variant: .secondary))
                    .disabled(isRetrying)
                    .frame(width: 150)
                }

                if let error {
                    AlertBanner(text: error)
                }

                VStack(spacing: 16) {
                    if session.response.results.isEmpty {
                        EmptyState(text: "Dishify did not return any recipes for this search.")
                    } else {
                        ForEach(session.response.results) { recipe in
                            RecipeCard(recipe: recipe)
                        }
                    }
                }

                DisclosureGroup("Pipeline details") {
                    VStack(spacing: 10) {
                        ForEach(session.response.stages) { stage in
                            HStack {
                                Text(stage.name)
                                Spacer()
                                Text(stage.status)
                                    .font(.system(size: 14, weight: .black))
                                Text("\(stage.latencyMs) ms")
                                    .foregroundStyle(Theme.Colors.muted)
                            }
                            .padding(12)
                            .background(Theme.Colors.surfaceMuted)
                            .clipShape(RoundedRectangle(cornerRadius: 8))
                        }
                    }
                    .padding(.top, 12)
                }
                .font(.system(size: 16, weight: .heavy))
            }
            .surfacePanel()
        } else {
            VStack(alignment: .leading, spacing: 16) {
                Eyebrow(text: "Recipe suggestions")
                Text("No results yet")
                    .font(.system(size: 40, weight: .black))
                Text("Add pantry ingredients and describe what sounds good first.")
                    .foregroundStyle(Theme.Colors.muted)
                Button("Start cooking") {
                    router.go(.cook)
                }
                .buttonStyle(PrimaryButtonStyle())
            }
            .surfacePanel()
        }
    }

    private func retry() async {
        guard let session else { return }
        error = nil
        isRetrying = true
        defer { isRetrying = false }
        do {
            let response = try await api.recommend(session.request)
            let next = RecommendationSession(request: session.request, response: response)
            RecommendationStore.save(next)
            self.session = next
        } catch {
            self.error = error.localizedDescription
        }
    }
}

struct EmptyState: View {
    let text: String

    var body: some View {
        Text(text)
            .foregroundStyle(Theme.Colors.muted)
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(16)
            .background(Color(red: 0.980, green: 0.969, blue: 0.949))
            .overlay(
                RoundedRectangle(cornerRadius: 8)
                    .stroke(Theme.Colors.border, style: StrokeStyle(lineWidth: 1, dash: [5]))
            )
    }
}
