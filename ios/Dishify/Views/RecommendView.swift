import SwiftUI

struct RecommendView: View {
	@EnvironmentObject private var auth: KeycloakAuthService
	@EnvironmentObject private var api: APIClient

	@State private var ingredientText = "tomato, pasta, mozzarella"
	@State private var recommendations: [RecommendationItem] = []
	@State private var isLoading = false
	@State private var errorMessage: String?

	var body: some View {
		List {
			Section("Ingredients") {
				TextField("tomato, pasta, ...", text: $ingredientText, axis: .vertical)
					.lineLimit(2 ... 4)
				Button(isLoading ? "Loading..." : "Recommend") {
					Task { await loadRecommendations() }
				}
				.disabled(isLoading)
			}

			if let errorMessage {
				Section {
					Text(errorMessage).foregroundStyle(.red)
				}
			}

			Section("Results") {
				if recommendations.isEmpty && !isLoading {
					Text("No recommendations yet.")
						.foregroundStyle(.secondary)
				}
				ForEach(recommendations) { item in
					VStack(alignment: .leading, spacing: 4) {
						Text(item.title).font(.headline)
						Text(String(format: "Score: %.0f%%", item.score * 100))
							.font(.subheadline)
							.foregroundStyle(.secondary)
						Text(item.reason)
							.font(.footnote)
					}
					.padding(.vertical, 4)
				}
			}
		}
		.toolbar {
			ToolbarItem(placement: .topBarTrailing) {
				Button("Sign out") { auth.logout() }
			}
		}
	}

	private func loadRecommendations() async {
		isLoading = true
		errorMessage = nil
		defer { isLoading = false }

		let ingredients = ingredientText
			.split(separator: ",")
			.map { $0.trimmingCharacters(in: .whitespacesAndNewlines) }
			.filter { !$0.isEmpty }

		guard !ingredients.isEmpty else {
			errorMessage = "Enter at least one ingredient."
			return
		}

		do {
			let response = try await api.recommend(ingredients: ingredients)
			recommendations = response.recommendations
		} catch {
			errorMessage = error.localizedDescription
		}
	}
}

#Preview {
	NavigationStack {
		RecommendView()
	}
	.environmentObject(KeycloakAuthService.shared)
	.environmentObject(APIClient.shared)
}
