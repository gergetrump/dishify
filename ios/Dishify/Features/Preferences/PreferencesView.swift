import SwiftUI

struct PreferencesView: View {
    @ObservedObject var viewModel: PreferencesViewModel

    var body: some View {
        NavigationStack {
            content
                .navigationTitle("Preferences")
                .searchable(text: $viewModel.searchText, prompt: "Search restrictions")
                .toolbar {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("Save") {
                            Task { await viewModel.save() }
                        }
                        .disabled(!viewModel.hasUnsavedChanges || viewModel.isSaving)
                        .accessibilityLabel("Save preferences")
                        .accessibilityHint(viewModel.hasUnsavedChanges ? "Saves your selected dietary restrictions." : "No changes to save.")
                    }
                }
                .task {
                    if case .idle = viewModel.loadState {
                        await viewModel.load()
                    }
                }
        }
    }

    @ViewBuilder
    private var content: some View {
        switch viewModel.loadState {
        case .idle, .loading:
            LoadingStateView(message: "Loading preferences…")
        case .failed(let message):
            ErrorStateView(message: message) {
                Task { await viewModel.load() }
            }
        case .loaded:
            preferencesList
        }
    }

    private var preferencesList: some View {
        List {
            if let statusMessage = viewModel.statusMessage {
                Section {
                    Label(statusMessage, systemImage: statusIcon(for: statusMessage))
                        .font(Theme.Typography.caption)
                        .foregroundStyle(statusColor(for: statusMessage))
                        .accessibilityLabel(statusMessage)
                }
            }

            if viewModel.filteredSections.isEmpty {
                Section {
                    IllustratedEmptyState(
                        systemImage: "leaf",
                        title: "No restrictions found",
                        message: "Try a different search term to find dietary restrictions."
                    )
                    .listRowInsets(EdgeInsets())
                    .listRowBackground(Color.clear)
                }
            } else {
                ForEach(viewModel.filteredSections, id: \.0) { category, tags in
                    Section(category.title) {
                        ForEach(tags) { tag in
                            Button {
                                viewModel.toggle(tag)
                            } label: {
                                HStack {
                                    Text(tag.label)
                                        .font(Theme.Typography.body)
                                        .foregroundStyle(Theme.Colors.textPrimary)
                                    Spacer()
                                    if viewModel.selectedTags.contains(tag.id) {
                                        Image(systemName: "checkmark.circle.fill")
                                            .foregroundStyle(Theme.Colors.accent)
                                    }
                                }
                            }
                            .frame(minHeight: Theme.Layout.minTapTarget)
                            .accessibilityLabel(tag.label)
                            .accessibilityValue(viewModel.selectedTags.contains(tag.id) ? "Selected" : "Not selected")
                            .accessibilityHint("Double tap to toggle this restriction.")
                        }
                    }
                }
            }
        }
        .listStyle(.insetGrouped)
        .overlay {
            if viewModel.isSaving {
                ProgressView("Saving…")
                    .padding(Theme.Spacing.md)
                    .background(Theme.Colors.surface)
                    .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.md))
                    .accessibilityLabel("Saving preferences")
            }
        }
    }

    private func statusColor(for message: String) -> Color {
        message == "Preferences saved." ? Theme.Colors.success : Theme.Colors.error
    }

    private func statusIcon(for message: String) -> String {
        message == "Preferences saved." ? "checkmark.circle.fill" : "exclamationmark.circle.fill"
    }
}

#Preview {
    PreferencesView(viewModel: PreferencesViewModel(session: SessionStore()))
}
