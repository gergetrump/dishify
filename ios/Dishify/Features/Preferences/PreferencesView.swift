import SwiftUI

struct PreferencesPage: View {
    @EnvironmentObject private var router: AppRouter

    @State private var selected: Set<String> = []
    @State private var error: String?
    @State private var status: String?
    @State private var isLoading = true
    @State private var isSaving = false

    private let api = APIClient()

    var body: some View {
        VStack(spacing: 0) {
            header

            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                    DishifyLogo(size: .compact)
                        .frame(maxWidth: .infinity)
                        .padding(.top, Theme.Spacing.sm)

                    Text("Choose allergies, diets, and restrictions Dishify should always avoid.")
                        .font(Theme.Fonts.body(15))
                        .foregroundStyle(Theme.Colors.muted)

                    if let error { AlertBanner(text: error) }
                    if let status { AlertBanner(text: status, kind: .success) }

                    HStack {
                        Text("\(selected.count) selected")
                            .foregroundStyle(Theme.Colors.muted)
                        Spacer()
                        TextLinkButton(title: "Clear all") {
                            status = nil
                            selected = []
                        }
                    }

                    if isLoading {
                        LoadingState(message: "Loading preferences...", branded: true)
                    }

                    VStack(alignment: .leading, spacing: Theme.Spacing.xxl) {
                        ForEach(restrictionSections) { section in
                            VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                                Text(section.title)
                                    .font(Theme.Fonts.display(18, weight: .bold))
                                Text(section.description)
                                    .font(Theme.Fonts.body(14))
                                    .foregroundStyle(Theme.Colors.muted)
                                FlowLayout(section.tags, spacing: 10) { tag in
                                    Chip(
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
                .padding(.horizontal, Theme.Spacing.screenPadding)
                .padding(.bottom, 100)
            }

            Button(isSaving ? "Saving..." : "Save preferences") {
                Task { await save() }
            }
            .buttonStyle(PrimaryButtonStyle())
            .disabled(isLoading || isSaving)
            .padding(Theme.Spacing.screenPadding)
            .background(Theme.Colors.background)
        }
        .screenBackground()
        .navigationBarHidden(true)
        .task {
            await load()
        }
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
            Text("Food preferences")
                .font(Theme.Fonts.display(18, weight: .bold))
                .foregroundStyle(Theme.Colors.text)
            Spacer()
            Color.clear.frame(width: 36, height: 36)
        }
        .padding(.horizontal, Theme.Spacing.screenPadding)
        .padding(.vertical, Theme.Spacing.md)
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
