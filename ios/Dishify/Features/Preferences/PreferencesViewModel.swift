import Foundation

@MainActor
final class PreferencesViewModel: ObservableObject {
    @Published private(set) var loadState: AsyncState<LoadMarker> = .idle
    @Published var selectedTags: Set<String> = []
    @Published var searchText = ""
    @Published var statusMessage: String?
    @Published private(set) var isSaving = false

    private let session: SessionStore
    private var savedTags: Set<String> = []

    var hasUnsavedChanges: Bool {
        selectedTags != savedTags
    }

    var filteredSections: [(RestrictionCategory, [RestrictionTag])] {
        RestrictionTags.grouped(matching: searchText)
    }

    init(session: SessionStore) {
        self.session = session
    }

    func load() async {
        loadState = .loading
        statusMessage = nil

        do {
            let client = try await session.makeAuthenticatedClient()
            let preferences: UserPreferences = try await client.request("/me/preferences", requiresAuth: true)
            let tags = Set(preferences.exclusionRestrictions)
            selectedTags = tags
            savedTags = tags
            loadState = .loaded(.ready)
        } catch {
            loadState = .failed(session.message(for: error, context: .preferences))
        }
    }

    func save() async {
        isSaving = true
        statusMessage = nil
        defer { isSaving = false }

        let sortedTags = selectedTags.sorted()

        do {
            let client = try await session.makeAuthenticatedClient()
            let preferences: UserPreferences = try await client.request(
                "/me/preferences",
                method: .put,
                body: PreferencesUpdateRequest(exclusionRestrictions: sortedTags),
                requiresAuth: true
            )
            let tags = Set(preferences.exclusionRestrictions)
            selectedTags = tags
            savedTags = tags
            loadState = .loaded(.ready)
            statusMessage = "Preferences saved."
        } catch {
            statusMessage = session.message(for: error, context: .preferences)
        }
    }

    func toggle(_ tag: RestrictionTag) {
        if selectedTags.contains(tag.id) {
            selectedTags.remove(tag.id)
        } else {
            selectedTags.insert(tag.id)
        }
    }
}
