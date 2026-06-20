import SwiftUI

struct PreferencesPage: View {
    @State private var selected: Set<String> = []
    @State private var error: String?
    @State private var status: String?
    @State private var isLoading = true
    @State private var isSaving = false

    private let api = APIClient()

    var body: some View {
        VStack(alignment: .leading, spacing: 24) {
            VStack(alignment: .leading, spacing: 8) {
                Eyebrow(text: "Hard filters")
                Text("Food preferences")
                    .font(.system(size: 40, weight: .black))
                Text("Choose allergies, diets, and restrictions Dishify should always avoid.")
                    .foregroundStyle(Theme.Colors.muted)
            }

            if let error { AlertBanner(text: error) }
            if let status { AlertBanner(text: status, kind: .success) }

            HStack {
                Text("\(selected.count) selected")
                    .foregroundStyle(Theme.Colors.muted)
                Spacer()
                Button("Clear all") {
                    status = nil
                    selected = []
                }
                .buttonStyle(PrimaryButtonStyle(variant: .ghost))
                .frame(width: 120)
                Button(isSaving ? "Saving..." : "Save preferences") {
                    Task { await save() }
                }
                .buttonStyle(PrimaryButtonStyle())
                .frame(width: 190)
                .disabled(isLoading || isSaving)
            }
            .padding(.vertical, 16)
            .overlay(Divider(), alignment: .top)
            .overlay(Divider(), alignment: .bottom)

            if isLoading {
                Text("Loading preferences...")
                    .foregroundStyle(Theme.Colors.muted)
            }

            VStack(alignment: .leading, spacing: 28) {
                ForEach(restrictionSections) { section in
                    VStack(alignment: .leading, spacing: 14) {
                        VStack(alignment: .leading, spacing: 4) {
                            Text(section.title)
                                .font(.system(size: 18, weight: .black))
                            Text(section.description)
                                .foregroundStyle(Theme.Colors.muted)
                        }
                        FlowLayout(section.tags, spacing: 10) { tag in
                            ChipButton(
                                title: formatRestrictionLabel(tag),
                                selected: selected.contains(tag),
                                disabled: isLoading
                            ) {
                                toggle(tag)
                            }
                        }
                    }
                }
            }
        }
        .surfacePanel()
        .task {
            await load()
        }
    }

    private func toggle(_ tag: String) {
        status = nil
        if selected.contains(tag) {
            selected.remove(tag)
        } else {
            selected.insert(tag)
        }
    }

    private func load() async {
        error = nil
        isLoading = true
        defer { isLoading = false }
        do {
            let preferences = try await api.preferences()
            selected = Set(preferences.exclusionRestrictions)
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func save() async {
        error = nil
        status = nil
        isSaving = true
        defer { isSaving = false }
        do {
            let preferences = try await api.updatePreferences(
                UpdatePreferencesRequest(exclusionRestrictions: Array(selected))
            )
            selected = Set(preferences.exclusionRestrictions)
            status = "Preferences saved."
        } catch {
            self.error = error.localizedDescription
        }
    }
}
