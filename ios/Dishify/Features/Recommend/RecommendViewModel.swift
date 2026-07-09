import SwiftUI

struct ResultsPage: View {
    @EnvironmentObject private var router: AppRouter

    @State private var session = RecommendationStore.load()
    @State private var error: String?
    @State private var isRetrying = false

    private let api = APIClient()

    var body: some View {
        VStack(spacing: 0) {
            header

            if let session {
                ScrollView {
                    VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
                        Text("For: \(session.request.query)")
                            .font(Theme.Fonts.body(14))
                            .foregroundStyle(Theme.Colors.muted)

                        if let error {
                            AlertBanner(text: error)
                        }

                        if session.response.results.isEmpty {
                            BrandedEmptyState(text: "Dishify did not return any recipes for this search.")
                        } else {
                            ForEach(session.response.results) { recipe in
                                RecipeCard(recipe: recipe)
                            }
                        }

                        DisclosureGroup("Pipeline details") {
                            VStack(spacing: Theme.Spacing.sm) {
                                ForEach(session.response.stages) { stage in
                                    HStack {
                                        Text(stage.name)
                                        Spacer()
                                        Text(stage.status)
                                            .font(Theme.Fonts.label(14, weight: .bold))
                                        Text("\(stage.latencyMs) ms")
                                            .foregroundStyle(Theme.Colors.muted)
                                    }
                                    .padding(Theme.Spacing.md)
                                    .background(Theme.Colors.cardBackground)
                                    .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.card))
                                }
                            }
                            .padding(.top, Theme.Spacing.md)
                        }
                        .font(Theme.Fonts.label(16, weight: .semibold))
                    }
                    .padding(.horizontal, Theme.Spacing.screenPadding)
                    .padding(.bottom, 100)
                }
                .onAppear {
                    AugmentCache.prefetchAll(session.response.results)
                }

                Button("Start over") {
                    router.popToRoot()
                }
                .buttonStyle(PrimaryButtonStyle())
                .padding(Theme.Spacing.screenPadding)
                .background(Theme.Colors.background)
            } else {
                VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
                    BrandedEmptyState(text: "Add pantry ingredients and describe what sounds good first.")
                    Button("Start cooking") {
                        router.popToRoot()
                    }
                    .buttonStyle(PrimaryButtonStyle())
                }
                .padding(Theme.Spacing.screenPadding)
                Spacer()
            }
        }
        .screenBackground()
        .navigationBarHidden(true)
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
            Text("Recipe suggestions")
                .font(Theme.Fonts.display(18, weight: .bold))
                .foregroundStyle(Theme.Colors.text)
            Spacer()
            HStack(spacing: Theme.Spacing.sm) {
                if session != nil {
                    Button(isRetrying ? "..." : "Retry") {
                        Task { await retry() }
                    }
                    .font(Theme.Fonts.label(14, weight: .semibold))
                    .foregroundStyle(Theme.Colors.primary)
                    .disabled(isRetrying)
                }
                ProfileToolbarButton { router.push(.profile) }
            }
        }
        .padding(.horizontal, Theme.Spacing.screenPadding)
        .padding(.vertical, Theme.Spacing.md)
    }

    private func retry() async {
        guard let session else { return }
        error = nil
        isRetrying = true
        defer { isRetrying = false }
        do {
            let response = try await api.recommend(session.request)
            AugmentCache.clear()
            let next = RecommendationSession(request: session.request, response: response)
            RecommendationStore.save(next)
            AugmentCache.prefetchAll(response.results)
            self.session = next
        } catch {
            self.error = error.localizedDescription
        }
    }
}
