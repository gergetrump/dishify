import SwiftUI

struct AuthView: View {
    @EnvironmentObject private var session: SessionStore

    @State private var showPasswordFallback = false
    @State private var isRegistering = false
    @State private var username = ""
    @State private var email = ""
    @State private var password = ""

    var body: some View {
        ScrollView {
            VStack(spacing: Theme.Spacing.lg) {
                branding

                Button(action: signInWithPKCE) {
                    Text("Sign in with Dishify")
                }
                .buttonStyle(PrimaryButtonStyle(isLoading: session.isLoading))
                .disabled(session.isLoading)
                .accessibilityLabel("Sign in with Dishify")
                .accessibilityHint("Opens secure browser sign in.")

                Button(showPasswordFallback ? "Hide username sign in" : "Use username and password instead") {
                    showPasswordFallback.toggle()
                    session.errorMessage = nil
                }
                .font(Theme.Typography.body)
                .foregroundStyle(Theme.Colors.accent)
                .frame(minHeight: Theme.Layout.minTapTarget)
                .accessibilityHint(showPasswordFallback ? "Hides the username and password form." : "Shows the username and password form.")

                if showPasswordFallback {
                    passwordFallbackForm
                }

                if let errorMessage = session.errorMessage {
                    ErrorBanner(message: errorMessage)
                }
            }
            .padding(Theme.Spacing.md)
            .frame(maxWidth: Theme.Layout.contentMaxWidth)
            .frame(maxWidth: .infinity)
        }
        .scrollDismissesKeyboard(.interactively)
        .background(Theme.Colors.background)
    }

    private var branding: some View {
        VStack(spacing: Theme.Spacing.md) {
            Image(systemName: "fork.knife.circle.fill")
                .font(.system(size: 56))
                .foregroundStyle(Theme.Colors.accent)
                .accessibilityHidden(true)

            Text("Dishify")
                .font(Theme.Typography.largeTitle)
                .foregroundStyle(Theme.Colors.textPrimary)

            Text("Sign in to get personalized recipe recommendations based on your pantry and dietary needs.")
                .font(Theme.Typography.body)
                .foregroundStyle(Theme.Colors.textSecondary)
                .multilineTextAlignment(.center)
        }
        .padding(.top, Theme.Spacing.xl)
        .accessibilityElement(children: .combine)
    }

    private var passwordFallbackForm: some View {
        VStack(spacing: Theme.Spacing.md) {
            Picker("Mode", selection: $isRegistering) {
                Text("Sign In").tag(false)
                Text("Register").tag(true)
            }
            .pickerStyle(.segmented)
            .accessibilityLabel("Account mode")

            authField(title: "Username", text: $username, contentType: .username)

            if isRegistering {
                authField(title: "Email", text: $email, contentType: .emailAddress)
            }

            authField(title: "Password", text: $password, contentType: .password, isSecure: true)

            Button(action: submitPasswordFlow) {
                Text(isRegistering ? "Create Account" : "Sign In")
            }
            .buttonStyle(PrimaryButtonStyle(isLoading: session.isLoading))
            .disabled(session.isLoading)
            .accessibilityLabel(isRegistering ? "Create account" : "Sign in")
        }
        .surfaceCard()
    }

    private func authField(
        title: String,
        text: Binding<String>,
        contentType: UITextContentType?,
        isSecure: Bool = false
    ) -> some View {
        LabeledFormField(label: title) {
            Group {
                if isSecure {
                    SecureField(title, text: text)
                } else {
                    TextField(title, text: text)
                }
            }
            .textContentType(contentType)
            .textInputAutocapitalization(isSecure ? .never : .none)
            .autocorrectionDisabled()
            .themedField()
            .accessibilityLabel(title)
        }
    }

    private func signInWithPKCE() {
        Task {
            await session.signIn()
        }
    }

    private func submitPasswordFlow() {
        Task {
            if isRegistering {
                await session.register(username: username, email: email, password: password)
            } else {
                await session.signIn(username: username, password: password)
            }
        }
    }
}

#Preview {
    AuthView()
        .environmentObject(SessionStore())
}
