import SwiftUI

struct WelcomePage: View {
    @EnvironmentObject private var session: SessionStore
    @EnvironmentObject private var router: AppRouter

    var body: some View {
        VStack(spacing: Theme.Spacing.xxl) {
            Spacer()

            WelcomeBowlIllustration()

            VStack(spacing: Theme.Spacing.md) {
                Text("Dishify")
                    .font(Theme.Fonts.display(36, weight: .bold))
                    .foregroundStyle(Theme.Colors.text)

                Text("Your next meal is already in your kitchen")
                    .font(Theme.Fonts.body(16))
                    .foregroundStyle(Theme.Colors.text)
                    .multilineTextAlignment(.center)
            }

            Spacer()

            VStack(spacing: Theme.Spacing.lg) {
                Button("Log in") { router.go(.login) }
                    .buttonStyle(PrimaryButtonStyle())

                TextLinkButton(title: "Sign up") { router.go(.register) }
            }
            .padding(.horizontal, Theme.Spacing.screenPadding)
            .padding(.bottom, Theme.Spacing.xxl)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .screenBackground()
        .navigationBarHidden(true)
        .onAppear {
            if session.isAuthenticated {
                router.resetToCook()
            }
        }
    }
}

struct LoginPage: View {
    @EnvironmentObject private var session: SessionStore
    @EnvironmentObject private var router: AppRouter

    @State private var username = ""
    @State private var password = ""
    @State private var error: String?
    @State private var isSubmitting = false

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                backButton { router.go(.welcome) }

                DishifyBrandMark(logoSize: .compact, showWordmark: false)
                    .padding(.bottom, Theme.Spacing.sm)

                Text("Log in")
                    .font(Theme.Fonts.display(32, weight: .bold))
                    .foregroundStyle(Theme.Colors.text)

                if let error {
                    AlertBanner(text: error)
                }

                VStack(spacing: Theme.Spacing.lg) {
                    LabeledField("Username") {
                        TextField("Username", text: $username)
                            .textInputAutocapitalization(.never)
                            .autocorrectionDisabled()
                            .textFieldStyle(DishifyTextFieldStyle())
                    }
                    LabeledField("Password") {
                        SecureField("Password", text: $password)
                            .textFieldStyle(DishifyTextFieldStyle())
                    }
                    Button(isSubmitting ? "Logging in..." : "Log in") {
                        Task { await submit() }
                    }
                    .buttonStyle(PrimaryButtonStyle())
                    .disabled(isSubmitting)
                }

                HStack(spacing: 4) {
                    Text("New here?")
                        .foregroundStyle(Theme.Colors.muted)
                    TextLinkButton(title: "Create an account") { router.go(.register) }
                }
            }
            .padding(Theme.Spacing.screenPadding)
            .frame(maxWidth: 400)
            .frame(maxWidth: .infinity)
        }
        .screenBackground()
        .navigationBarHidden(true)
    }

    private func submit() async {
        error = nil
        isSubmitting = true
        defer { isSubmitting = false }
        do {
            try await session.login(username: username, password: password)
            router.resetToCook()
        } catch {
            self.error = error.localizedDescription
        }
    }
}

struct RegisterPage: View {
    @EnvironmentObject private var session: SessionStore
    @EnvironmentObject private var router: AppRouter

    @State private var username = ""
    @State private var email = ""
    @State private var password = ""
    @State private var selected: Set<String> = []
    @State private var error: String?
    @State private var isSubmitting = false

    private var initialTags: [String] {
        Array(restrictionSections.prefix(2).flatMap { $0.tags.prefix(8) })
    }

    var body: some View {
        ScrollView {
            VStack(alignment: .leading, spacing: Theme.Spacing.xl) {
                backButton { router.go(.welcome) }

                DishifyBrandMark(logoSize: .compact, showWordmark: false)
                    .padding(.bottom, Theme.Spacing.sm)

                Text("Sign up")
                    .font(Theme.Fonts.display(32, weight: .bold))
                    .foregroundStyle(Theme.Colors.text)

                if let error {
                    AlertBanner(text: error)
                }

                LabeledField("Username") {
                    TextField("Username", text: $username)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .textFieldStyle(DishifyTextFieldStyle())
                }
                LabeledField("Email") {
                    TextField("Email", text: $email)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .textFieldStyle(DishifyTextFieldStyle())
                }
                LabeledField("Password") {
                    SecureField("Password", text: $password)
                        .textFieldStyle(DishifyTextFieldStyle())
                }

                VStack(alignment: .leading, spacing: Theme.Spacing.md) {
                    Text("Initial preferences")
                        .font(Theme.Fonts.label(16, weight: .bold))
                    Text("Optional. You can change these later.")
                        .font(Theme.Fonts.body(14))
                        .foregroundStyle(Theme.Colors.muted)
                    FlowLayout(initialTags, spacing: 10) { tag in
                        Chip(title: formatRestrictionLabel(tag), selected: selected.contains(tag)) {
                            toggle(tag)
                        }
                    }
                }

                Button(isSubmitting ? "Creating account..." : "Sign up") {
                    Task { await submit() }
                }
                .buttonStyle(PrimaryButtonStyle())
                .disabled(isSubmitting)

                HStack(spacing: 4) {
                    Text("Already have an account?")
                        .foregroundStyle(Theme.Colors.muted)
                    TextLinkButton(title: "Log in") { router.go(.login) }
                }
            }
            .padding(Theme.Spacing.screenPadding)
            .frame(maxWidth: 400)
            .frame(maxWidth: .infinity)
        }
        .screenBackground()
        .navigationBarHidden(true)
    }

    private func toggle(_ tag: String) {
        if selected.contains(tag) {
            selected.remove(tag)
        } else {
            selected.insert(tag)
        }
    }

    private func submit() async {
        error = nil
        isSubmitting = true
        defer { isSubmitting = false }
        do {
            try await session.register(
                username: username,
                email: email,
                password: password,
                exclusionRestrictions: Array(selected)
            )
            router.resetToCook()
        } catch {
            self.error = error.localizedDescription
        }
    }
}

private func backButton(action: @escaping () -> Void) -> some View {
    Button(action: action) {
        Text("Back")
            .font(Theme.Fonts.label(16, weight: .semibold))
            .foregroundStyle(Theme.Colors.primary)
    }
}
