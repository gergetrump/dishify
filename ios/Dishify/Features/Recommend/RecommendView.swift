import SwiftUI

struct PantryPage: View {
    @EnvironmentObject private var router: AppRouter

    @State private var items = PantryStore.load()
    @State private var editingID: String?
    @State private var name = ""
    @State private var quantity = ""
    @State private var unit = ""
    @State private var nameFocused = false
    @State private var error: String?
    @State private var showCapture = false
    @State private var isRecording = false
    @State private var isTranscribing = false
    @State private var mediaNotice: String?

    private let api = APIClient()
    private let voiceService = VoiceInputService()

    var body: some View {
        VStack(spacing: 0) {
            header

            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.lg) {
                    HStack {
                        Text("Add all the ingredients you have.")
                            .font(Theme.Fonts.body(15))
                            .foregroundStyle(Theme.Colors.muted)
                        Spacer()
                        if !items.isEmpty {
                            Button("Clear all") {
                                items = []
                                resetForm()
                            }
                            .font(Theme.Fonts.label(15, weight: .semibold))
                            .foregroundStyle(Theme.Colors.missing)
                        }
                    }

                    HStack(spacing: Theme.Spacing.md) {
                        Button {
                            showCapture = true
                        } label: {
                            Label("Scan ingredients", systemImage: "camera")
                                .font(Theme.Fonts.label(14, weight: .semibold))
                                .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(PrimaryButtonStyle(variant: .secondary))

                        Button {
                            Task { await toggleVoice() }
                        } label: {
                            Label(
                                isTranscribing ? "Listening..." : (isRecording ? "Stop" : "Say what you have"),
                                systemImage: isRecording ? "stop.circle" : "mic"
                            )
                            .font(Theme.Fonts.label(14, weight: .semibold))
                            .frame(maxWidth: .infinity)
                        }
                        .buttonStyle(PrimaryButtonStyle(variant: .secondary))
                        .disabled(isTranscribing)
                    }

                    if let mediaNotice {
                        AlertBanner(text: mediaNotice, kind: .success)
                    }

                    if items.isEmpty {
                        BrandedEmptyState(text: "No ingredients yet. Add what you have in your kitchen.")
                    } else {
                        ForEach(items) { item in
                            IngredientCard(
                                name: item.name,
                                detail: item.rawText,
                                onEdit: { edit(item) },
                                onDelete: { delete(item) }
                            )
                        }
                    }

                    if let error {
                        AlertBanner(text: error)
                    }
                }
                .padding(.horizontal, Theme.Spacing.screenPadding)
                .padding(.bottom, Theme.Spacing.lg)
            }

            inputArea
        }
        .screenBackground()
        .navigationBarHidden(true)
        .sheet(isPresented: $showCapture) {
            IngredientCaptureView { detected in
                addDetectedIngredients(detected)
            }
        }
        .onChange(of: items) { updatedItems in
            PantryStore.save(updatedItems)
        }
    }

    private var header: some View {
        HStack {
            DishifyLogo(size: .icon)
            Spacer()
            Text("What's available today?")
                .font(Theme.Fonts.display(18, weight: .bold))
                .foregroundStyle(Theme.Colors.text)
                .multilineTextAlignment(.center)
            Spacer()
            ProfileToolbarButton { router.push(.profile) }
        }
        .padding(.horizontal, Theme.Spacing.screenPadding)
        .padding(.vertical, Theme.Spacing.md)
    }

    private var inputArea: some View {
        VStack(spacing: Theme.Spacing.md) {
            TextField("Ingredient name", text: $name)
                .font(Theme.Fonts.body(16))
                .padding(.horizontal, 14)
                .frame(minHeight: 48)
                .background(Color.white)
                .overlay(
                    RoundedRectangle(cornerRadius: Theme.Radius.input)
                        .stroke(nameFocused ? Theme.Colors.primary : Theme.Colors.border, lineWidth: nameFocused ? 2 : 1)
                )
                .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.input))
                .onTapGesture { nameFocused = true }

            HStack(spacing: Theme.Spacing.md) {
                TextField("Quantity", text: $quantity)
                    .keyboardType(.decimalPad)
                    .textFieldStyle(DishifyTextFieldStyle())
                TextField("Unit", text: $unit)
                    .textFieldStyle(DishifyTextFieldStyle())

                Button {
                    saveIngredient()
                } label: {
                    Image(systemName: "plus")
                        .font(.system(size: 20, weight: .bold))
                        .foregroundStyle(Color("PrimaryActionText"))
                        .frame(width: 48, height: 48)
                        .background(Theme.Colors.primary)
                        .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.button))
                }
            }

            Button("Set your vibe") {
                router.push(.vibe)
            }
            .buttonStyle(PrimaryButtonStyle())
            .disabled(items.isEmpty)
            .opacity(items.isEmpty ? 0.5 : 1)
        }
        .padding(Theme.Spacing.screenPadding)
        .background(Theme.Colors.background)
    }

    private func saveIngredient() {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        if let failure = InputValidation.validate(trimmed) {
            error = InputValidation.message(for: failure)
            return
        }
        error = nil
        let parsedQuantity = Double(quantity.trimmingCharacters(in: .whitespacesAndNewlines))
        let next = PantryStore.make(name: trimmed, quantity: parsedQuantity, unit: unit)

        if let editingID {
            items = items.map {
                $0.id == editingID
                    ? ParsedIngredient(id: editingID, name: next.name, quantity: next.quantity, unit: next.unit, rawText: next.rawText)
                    : $0
            }
        } else {
            items.append(next)
        }
        resetForm()
        nameFocused = false
    }

    private func edit(_ item: ParsedIngredient) {
        editingID = item.id
        name = item.name
        quantity = item.quantity.map { String(format: "%g", $0) } ?? ""
        unit = item.unit ?? ""
        nameFocused = true
    }

    private func delete(_ item: ParsedIngredient) {
        items.removeAll { $0.id == item.id }
        if editingID == item.id { resetForm() }
    }

    private func resetForm() {
        editingID = nil
        name = ""
        quantity = ""
        unit = ""
    }

    private func addDetectedIngredients(_ detected: [DetectedIngredient]) {
        for item in detected {
            let next = PantryStore.make(name: item.name, quantity: item.quantity, unit: item.unit ?? "")
            items.append(next)
        }
        mediaNotice = "Added \(detected.count) ingredient\(detected.count == 1 ? "" : "s") from photo."
    }

    private func toggleVoice() async {
        error = nil
        mediaNotice = nil
        if isRecording {
            isRecording = false
            isTranscribing = true
            defer { isTranscribing = false }
            do {
                let result = try await voiceService.stopAndTranscribe(api: api)
                applyVoiceResult(result)
            } catch {
                self.error = error.localizedDescription
            }
        } else {
            do {
                try await voiceService.startRecording()
                isRecording = true
            } catch {
                self.error = error.localizedDescription
            }
        }
    }

    private func applyVoiceResult(_ result: VoiceResponse) {
        for item in result.ingredients {
            let next = PantryStore.make(name: item.name, quantity: item.quantity, unit: item.unit ?? "")
            items.append(next)
        }
        if let spokenQuery = result.query, !spokenQuery.isEmpty {
            VibeDraftStore.save(spokenQuery)
        }
        if result.ingredients.isEmpty {
            if let spokenQuery = result.query, !spokenQuery.isEmpty {
                mediaNotice = "Saved vibe for the next step: \"\(spokenQuery)\""
            } else {
                mediaNotice = "Heard: \"\(result.transcript)\""
            }
        } else if let spokenQuery = result.query, !spokenQuery.isEmpty {
            mediaNotice = "Added \(result.ingredients.count) ingredient\(result.ingredients.count == 1 ? "" : "s") and saved your vibe."
        } else {
            mediaNotice = "Added \(result.ingredients.count) ingredient\(result.ingredients.count == 1 ? "" : "s") from voice."
        }
    }
}

// Legacy alias
typealias CookPage = PantryPage

struct VibePage: View {
    @EnvironmentObject private var router: AppRouter

    @State private var items = PantryStore.load()
    @State private var query = ""
    @State private var topK = 5
    @State private var error: String?
    @State private var isSubmitting = false

    private let api = APIClient()
    private let examplePrompts = [
        "quick high-protein dinner",
        "cozy vegetarian pasta",
        "spicy lunch with eggs",
    ]

    var body: some View {
        VStack(spacing: 0) {
            header

            ScrollView {
                VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                    DishifyLogo(size: .compact)
                        .frame(maxWidth: .infinity)

                    Text("Describe what sounds good, or leave blank and Dishify will use your pantry.")
                        .font(Theme.Fonts.body(15))
                        .foregroundStyle(Theme.Colors.muted)

                    if let error {
                        AlertBanner(text: error)
                    }

                    LabeledField("Eating vibe", hint: "optional") {
                        TextEditor(text: $query)
                            .font(Theme.Fonts.body(16))
                            .frame(minHeight: 120)
                            .padding(10)
                            .background(Color.white)
                            .overlay(
                                RoundedRectangle(cornerRadius: Theme.Radius.input)
                                    .stroke(Theme.Colors.border, lineWidth: 1)
                            )
                            .clipShape(RoundedRectangle(cornerRadius: Theme.Radius.input))
                            .onChange(of: query) { newValue in
                                if newValue.count > 512 {
                                    query = String(newValue.prefix(512))
                                }
                            }
                    }

                    FlowLayout(examplePrompts, spacing: 10) { prompt in
                        Button {
                            query = prompt
                        } label: {
                            Text(prompt)
                                .font(Theme.Fonts.label(14, weight: .semibold))
                                .foregroundStyle(Theme.Colors.primaryDark)
                                .padding(.horizontal, 12)
                                .padding(.vertical, 9)
                                .background(Color(red: 1, green: 0.945, blue: 0.918))
                                .clipShape(Capsule())
                        }
                    }

                    VStack(alignment: .leading, spacing: Theme.Spacing.sm) {
                        Text("Number of results")
                            .font(Theme.Fonts.label(14, weight: .semibold))
                        Picker("Results", selection: $topK) {
                            Text("3").tag(3)
                            Text("5").tag(5)
                            Text("10").tag(10)
                        }
                        .pickerStyle(.segmented)
                    }
                }
                .padding(.horizontal, Theme.Spacing.screenPadding)
                .padding(.bottom, 100)
            }

            VStack {
                Button(isSubmitting ? "Finding recipes..." : "Show recipes") {
                    Task { await recommend() }
                }
                .buttonStyle(PrimaryButtonStyle())
                .disabled(isSubmitting)
            }
            .padding(Theme.Spacing.screenPadding)
            .background(Theme.Colors.background)
        }
        .screenBackground()
        .navigationBarHidden(true)
        .onAppear {
            items = PantryStore.load()
            let draft = VibeDraftStore.load()
            if !draft.isEmpty {
                query = draft
                VibeDraftStore.clear()
            }
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
            Text("Set your vibe")
                .font(Theme.Fonts.display(18, weight: .bold))
                .foregroundStyle(Theme.Colors.text)
            Spacer()
            ProfileToolbarButton { router.push(.profile) }
        }
        .padding(.horizontal, Theme.Spacing.screenPadding)
        .padding(.vertical, Theme.Spacing.md)
    }

    private func recommend() async {
        error = nil
        isSubmitting = true
        defer { isSubmitting = false }

        items = PantryStore.load()
        let resolvedQuery = query.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? defaultQueryFromPantry()
            : query.trimmingCharacters(in: .whitespacesAndNewlines)
        if let failure = InputValidation.validate(resolvedQuery) {
            error = InputValidation.message(for: failure)
            return
        }
        for item in items {
            if let failure = InputValidation.validate(item.name) {
                error = "Pantry ingredient \"\(item.name)\" is invalid: \(InputValidation.message(for: failure))"
                return
            }
        }
        let request = RecommendRequest(
            query: resolvedQuery,
            topK: topK,
            availableIngredients: items.map {
                ParsedIngredient(id: nil, name: $0.name, quantity: $0.quantity, unit: $0.unit, rawText: $0.rawText)
            },
            exclusionRestrictions: nil
        )

        do {
            let response = try await api.recommend(request)
            AugmentCache.clear()
            RecommendationStore.save(RecommendationSession(request: request, response: response))
            AugmentCache.prefetchAll(response.results)
            router.push(.results)
        } catch {
            self.error = error.localizedDescription
        }
    }

    private func defaultQueryFromPantry() -> String {
        if items.isEmpty { return "recipe recommendation" }
        let names = items.prefix(8).map(\.name).joined(separator: ", ")
        return "recipe using \(names)"
    }
}
