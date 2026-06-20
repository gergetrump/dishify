import SwiftUI

struct WelcomePage: View {
    @EnvironmentObject private var session: SessionStore
    @EnvironmentObject private var router: AppRouter

    var body: some View {
        if session.isAuthenticated {
            CookPage()
                .onAppear { router.go(.cook) }
        } else {
            VStack(spacing: 24) {
                VStack(alignment: .leading, spacing: 18) {
                    Eyebrow(text: "Dishify")
                    Text("Your next meal is already in your kitchen.")
                        .font(.system(size: 52, weight: .black))
                        .lineSpacing(-8)
                        .foregroundStyle(Theme.Colors.text)
                    Text("Add what you have, set the foods you avoid, and get recipe ideas that fit your pantry.")
                        .font(.system(size: 17))
                        .lineSpacing(6)
                        .foregroundStyle(Theme.Colors.muted)

                    HStack(spacing: 12) {
                        Button("Sign up") { router.go(.register) }
                            .buttonStyle(PrimaryButtonStyle())
                        Button("Log in") { router.go(.login) }
                            .buttonStyle(PrimaryButtonStyle(variant: .secondary))
                    }
                }
                .surfacePanel()

                HStack(spacing: 14) {
                    FoodShape(color: Color(red: 1.0, green: 0.592, blue: 0.208), rotation: -18)
                    FoodShape(color: Color(red: 0.937, green: 0.388, blue: 0.282), rotation: 0)
                    FoodShape(color: Color(red: 0.373, green: 0.663, blue: 0.353), rotation: 18)
                }
                .frame(maxWidth: .infinity, minHeight: 260)
                .background(Color(red: 0.863, green: 0.937, blue: 0.851))
                .overlay(
                    RoundedRectangle(cornerRadius: 8)
                        .stroke(Color(red: 0.780, green: 0.875, blue: 0.780), lineWidth: 1)
                )
                .clipShape(RoundedRectangle(cornerRadius: 8))
                .shadow(color: Color.black.opacity(0.08), radius: 24, x: 0, y: 12)
            }
        }
    }
}

private struct FoodShape: View {
    let color: Color
    let rotation: Double

    var body: some View {
        RoundedRectangle(cornerRadius: 28)
            .fill(color)
            .frame(width: 72, height: 72)
            .rotationEffect(.degrees(rotation))
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
        VStack(alignment: .leading, spacing: 16) {
            Eyebrow(text: "Welcome back")
            Text("Log in to Dishify")
                .font(.system(size: 36, weight: .black))
                .foregroundStyle(Theme.Colors.text)

            if let error {
                AlertBanner(text: error)
            }

            VStack(spacing: 12) {
                FieldLabel("Username") {
                    TextField("Username", text: $username)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .textFieldStyle(WebTextFieldStyle())
                }
                FieldLabel("Password") {
                    SecureField("Password", text: $password)
                        .textFieldStyle(WebTextFieldStyle())
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
                Button("Create an account") { router.go(.register) }
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(Theme.Colors.primaryDark)
            }
        }
        .frame(maxWidth: 440)
        .surfacePanel()
        .frame(maxWidth: .infinity)
    }

    private func submit() async {
        error = nil
        isSubmitting = true
        defer { isSubmitting = false }
        do {
            try await session.login(username: username, password: password)
            router.go(.cook)
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
        VStack(alignment: .leading, spacing: 16) {
            Eyebrow(text: "Start cooking smarter")
            Text("Create your account")
                .font(.system(size: 36, weight: .black))
                .foregroundStyle(Theme.Colors.text)

            if let error {
                AlertBanner(text: error)
            }

            FieldLabel("Username") {
                TextField("Username", text: $username)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .textFieldStyle(WebTextFieldStyle())
            }
            FieldLabel("Email") {
                TextField("Email", text: $email)
                    .keyboardType(.emailAddress)
                    .textInputAutocapitalization(.never)
                    .autocorrectionDisabled()
                    .textFieldStyle(WebTextFieldStyle())
            }
            FieldLabel("Password") {
                SecureField("Password", text: $password)
                    .textFieldStyle(WebTextFieldStyle())
            }

            VStack(alignment: .leading, spacing: 12) {
                Divider()
                Text("Initial preferences")
                    .font(.system(size: 17, weight: .black))
                Text("Optional. You can change these later.")
                    .foregroundStyle(Theme.Colors.muted)
                FlowLayout(initialTags, spacing: 10) { tag in
                    ChipButton(title: formatRestrictionLabel(tag), selected: selected.contains(tag)) {
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
                Button("Log in") { router.go(.login) }
                    .font(.system(size: 16, weight: .bold))
                    .foregroundStyle(Theme.Colors.primaryDark)
            }
        }
        .frame(maxWidth: 440)
        .surfacePanel()
        .frame(maxWidth: .infinity)
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
            router.go(.cook)
        } catch {
            self.error = error.localizedDescription
        }
    }
}
