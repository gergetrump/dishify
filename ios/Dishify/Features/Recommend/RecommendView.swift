import SwiftUI

struct RecommendView: View {
    @ObservedObject var viewModel: RecommendViewModel

    var body: some View {
        NavigationStack {
            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
                    querySection
                    pantrySection
                    recommendButton

                    if let message = viewModel.state.errorMessage {
                        ErrorBanner(message: message)
                    }

                    if let notice = viewModel.stageNotice {
                        NoticeBanner(message: notice)
                    }

                    resultsSection
                }
                .padding(Theme.Spacing.md)
                .frame(maxWidth: Theme.Layout.contentMaxWidth)
                .frame(maxWidth: .infinity)
            }
            .scrollDismissesKeyboard(.interactively)
            .background(Theme.Colors.background)
            .navigationTitle("Recommend")
        }
        .onDisappear {
            viewModel.cancel()
        }
    }

    private var querySection: some View {
        VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
            SectionHeader(
                title: "What would you like to cook?",
                subtitle: "Describe a dish, cuisine, or craving."
            )

            TextField("e.g. creamy tomato pasta with spinach", text: $viewModel.query, axis: .vertical)
                .lineLimit(2...4)
                .textInputAutocapitalization(.sentences)
                .themedField()
                .accessibilityLabel("Recipe search")
                .accessibilityHint("Describe what you want to cook.")

            Stepper(value: $viewModel.topK, in: 1...100) {
                Text("Results: \(viewModel.topK)")
                    .font(Theme.Typography.body)
                    .foregroundStyle(Theme.Colors.textSecondary)
            }
            .accessibilityLabel("Number of results")
            .accessibilityValue("\(viewModel.topK)")
        }
        .surfaceCard()
    }

    private var pantrySection: some View {
        PantryEditor(ingredients: $viewModel.pantryIngredients)
            .surfaceCard()
    }

    private var recommendButton: some View {
        VStack(spacing: Theme.Spacing.sm) {
            Button {
                Task { await viewModel.recommend() }
            } label: {
                Text("Find Recipes")
            }
            .buttonStyle(PrimaryButtonStyle(isLoading: viewModel.state.isLoading))
            .disabled(viewModel.state.isLoading)
            .accessibilityLabel("Find recipes")
            .accessibilityHint("Searches for recipes matching your query and pantry.")

            if viewModel.state.isLoading {
                Button(role: .cancel) {
                    viewModel.cancel()
                } label: {
                    Text("Cancel")
                        .frame(maxWidth: .infinity)
                }
                .accessibilityLabel("Cancel search")
                .accessibilityHint("Stops the current recipe search.")
            }

            #if DEBUG
            Toggle("Debug: Skip auth for recommend", isOn: $viewModel.debugSkipAuthForRecommend)
                .font(Theme.Typography.caption)
                .tint(Theme.Colors.accent)
                .accessibilityHint("Sends recommend request without bearer token.")
            #endif
        }
    }

    @ViewBuilder
    private var resultsSection: some View {
        switch viewModel.state {
        case .idle:
            IllustratedEmptyState(
                systemImage: "magnifyingglass",
                title: "Ready to search",
                message: "Enter what you'd like to cook, optionally add pantry items, then tap Find Recipes."
            )
        case .loading:
            InlineLoadingRow(message: "Searching recipes…")
        case .failed:
            EmptyView()
        case .loaded(let response):
            if response.results.isEmpty {
                IllustratedEmptyState(
                    systemImage: "tray",
                    title: "No matches found",
                    message: "Try a broader search or adjust your pantry ingredients."
                )
            } else {
                VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
                    Text("Results")
                        .font(Theme.Typography.headline)
                        .foregroundStyle(Theme.Colors.textPrimary)
                        .accessibilityAddTraits(.isHeader)

                    ForEach(response.results, id: \.id) { result in
                        NavigationLink {
                            ResultDetailView(result: result)
                        } label: {
                            ResultRow(result: result)
                        }
                        .buttonStyle(.plain)
                        .accessibilityLabel(resultAccessibilityLabel(for: result))
                        .accessibilityHint("Opens recipe details.")
                    }
                }
            }
        }
    }

    private func resultAccessibilityLabel(for result: RecipeResult) -> String {
        var parts = [
            "Rank \(result.rank)",
            result.title,
            RecipeResultFormatting.matchLabel(for: result.score),
        ]

        if !result.inventoryMatched.isEmpty {
            parts.append("\(result.inventoryMatched.count) pantry items matched")
        }
        if !result.inventoryMissing.isEmpty {
            parts.append("\(result.inventoryMissing.count) pantry items missing")
        }

        return parts.joined(separator: ", ")
    }
}

#Preview {
    RecommendView(viewModel: RecommendViewModel(session: SessionStore()))
}
