import Foundation

@MainActor
final class RecommendViewModel: ObservableObject {
    private static let recommendTimeoutSeconds: Duration = .seconds(45)

    @Published private(set) var state: AsyncState<RecommendResponse> = .idle
    @Published var query = ""
    @Published var topK = 5
    @Published var pantryIngredients: [ParsedIngredient] = []
    #if DEBUG
    @Published var debugSkipAuthForRecommend = false
    #endif

    private let session: SessionStore
    private var recommendTask: Task<Void, Never>?

    var results: [RecipeResult] {
        state.value?.results ?? []
    }

    var stageNotice: String? {
        guard let response = state.value else {
            return nil
        }

        guard let explainStage = response.stages.first(where: { $0.name == "explain" }) else {
            return nil
        }

        switch explainStage.status {
        case "skipped":
            return "AI explanations are unavailable for this search."
        case "error":
            return "We couldn't generate explanations for these results."
        default:
            return nil
        }
    }

    init(session: SessionStore) {
        self.session = session
    }

    func recommend() async {
        let trimmedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmedQuery.isEmpty else {
            state = .failed("Enter what you'd like to cook.")
            return
        }

        recommendTask?.cancel()

        state = .loading

        let request = RecommendRequest(
            query: trimmedQuery,
            topK: min(max(topK, 1), 100),
            availableIngredients: pantryIngredients.isEmpty ? nil : pantryIngredients,
            exclusionRestrictions: nil
        )
        #if DEBUG
        let skipAuthForRecommend = debugSkipAuthForRecommend
        #endif

        let task = Task { [weak self] in
            guard let self else { return }
            do {
                let response = try await Self.withTimeout(Self.recommendTimeoutSeconds) {
                    #if DEBUG
                    if skipAuthForRecommend {
                        return try await APIClient().request(
                            "/recommend",
                            method: .post,
                            body: request,
                            requiresAuth: false
                        ) as RecommendResponse
                    }
                    #endif

                    let client = try await self.session.makeAuthenticatedClient()
                    return try await client.request(
                        "/recommend",
                        method: .post,
                        body: request,
                        requiresAuth: true
                    ) as RecommendResponse
                }
                try Task.checkCancellation()
                self.state = .loaded(response)
            } catch is CancellationError {
                return
            } catch TimeoutError.recommendRequestTimedOut {
                self.state = .failed("Request timed out. Please try again.")
            } catch {
                if (error as? URLError)?.code == .cancelled { return }
                self.state = .failed(self.session.message(for: error, context: .recommend))
            }
        }

        recommendTask = task
        await task.value
    }

    func cancel() {
        recommendTask?.cancel()
        recommendTask = nil
        if state.isLoading {
            state = .idle
        }
    }

    private enum TimeoutError: Error {
        case recommendRequestTimedOut
    }

    private static func withTimeout<T: Sendable>(
        _ timeout: Duration,
        operation: @escaping @Sendable () async throws -> T
    ) async throws -> T {
        try await withThrowingTaskGroup(of: T.self) { group in
            group.addTask {
                try await operation()
            }
            group.addTask {
                try await Task.sleep(for: timeout)
                throw TimeoutError.recommendRequestTimedOut
            }

            guard let firstResult = try await group.next() else {
                group.cancelAll()
                throw TimeoutError.recommendRequestTimedOut
            }
            group.cancelAll()
            return firstResult
        }
    }
}
