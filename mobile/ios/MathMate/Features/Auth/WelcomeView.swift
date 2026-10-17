import SwiftUI

/// Sign in, sign up or try without an account (web/src/routes/auth.tsx).
struct WelcomeView: View {
    @Environment(SessionStore.self) private var session
    @State private var registering = false

    var body: some View {
        ScrollView {
            VStack(spacing: 24) {
                VStack(spacing: 8) {
                    Image("Logo")
                        .resizable()
                        .frame(width: 72, height: 72)
                        .clipShape(.rect(cornerRadius: 17, style: .continuous))
                        .shadow(color: .black.opacity(0.12), radius: 8, y: 4)
                        .accessibilityHidden(true)
                    Text(Brand.appName).font(.largeTitle.bold())
                    Text("Gia sư toán THCS – THPT, kèm hình vẽ minh họa")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                        .multilineTextAlignment(.center)
                }
                .padding(.top, 32)

                if let error = session.startError {
                    Label(error, systemImage: "wifi.exclamationmark")
                        .font(.footnote)
                        .foregroundStyle(.orange)
                        .multilineTextAlignment(.center)
                }

                Group {
                    if registering {
                        RegisterForm(onLogin: { withAnimation { registering = false } })
                    } else {
                        LoginForm(onRegister: { withAnimation { registering = true } })
                    }
                }
                .padding(20)
                .background(.background, in: .rect(cornerRadius: 20))
                .overlay(RoundedRectangle(cornerRadius: 20).stroke(.separator, lineWidth: 0.5))
                .frame(maxWidth: 420)

                VStack(spacing: 4) {
                    Button("Dùng thử không cần tài khoản →") {
                        Task { await session.continueAsGuest() }
                    }
                    .accessibilityIdentifier("tryAsGuest")
                    Text("Khi dùng thử, lịch sử chỉ lưu trên máy này.")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
            .padding(.horizontal, 16)
            .padding(.bottom, 32)
            .frame(maxWidth: .infinity)
        }
        .background(Color(.systemGroupedBackground).ignoresSafeArea())
        .scrollDismissesKeyboard(.interactively)
    }
}

/// A labelled text field in the style of the web forms.
private struct Field: View {
    let label: String
    @Binding var text: String
    var secure = false
    var placeholder = ""
    var contentType: UITextContentType?
    var identifier: String

    var body: some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(label).font(.subheadline.weight(.medium))
            Group {
                if secure {
                    SecureField(placeholder, text: $text)
                } else {
                    TextField(placeholder, text: $text)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                }
            }
            // In the Simulator, password AutoFill takes the keyboard's place for a username and
            // password pair and shows nothing, so UI tests could not type; real devices show the
            // keyboard with password suggestions.
            .textContentType(UITesting.isActive ? .oneTimeCode : contentType)
            .padding(.horizontal, 12)
            .frame(height: 44)
            .background(Color(.secondarySystemBackground), in: .rect(cornerRadius: 10))
            .accessibilityIdentifier(identifier)
            .accessibilityLabel(label)
        }
    }
}

private struct FormError: View {
    let message: String?

    var body: some View {
        if let message {
            Text(message)
                .font(.footnote)
                .foregroundStyle(.red)
                .frame(maxWidth: .infinity, alignment: .leading)
                .accessibilityIdentifier("authError")
        }
    }
}

private struct LoginForm: View {
    @Environment(SessionStore.self) private var session
    let onRegister: () -> Void
    @State private var username = ""
    @State private var password = ""
    @State private var error: String?
    @State private var busy = false

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 4) {
                Text("Đăng nhập").font(.title2.bold())
                Text("Đăng nhập để xem lại lịch sử hỏi đáp.").font(.subheadline).foregroundStyle(.secondary)
            }
            Field(label: "Tên đăng nhập", text: $username, contentType: .username, identifier: "username")
            Field(label: "Mật khẩu", text: $password, secure: true, contentType: .password, identifier: "password")
            FormError(message: error)
            Button {
                Task { await submit() }
            } label: {
                Group { if busy { ProgressView() } else { Text("Đăng nhập") } }
                    .frame(maxWidth: .infinity, minHeight: 32)
            }
            .mmGlassButton(prominent: true)
            .disabled(busy || username.isEmpty || password.isEmpty)
            .accessibilityIdentifier("loginButton")
            HStack(spacing: 4) {
                Text("Chưa có tài khoản?").foregroundStyle(.secondary)
                Button("Đăng ký", action: onRegister).accessibilityIdentifier("showRegister")
            }
            .font(.subheadline)
            .frame(maxWidth: .infinity)
        }
        .onSubmit { Task { await submit() } }
    }

    private func submit() async {
        guard !busy, !username.isEmpty, !password.isEmpty else { return }
        busy = true
        defer { busy = false }
        do {
            try await session.login(username: username, password: password)
        } catch {
            self.error = error.localizedDescription
            password = ""
            Haptics.warning()
        }
    }
}

private struct RegisterForm: View {
    @Environment(SessionStore.self) private var session
    let onLogin: () -> Void
    @State private var username = ""
    @State private var password = ""
    @State private var confirm = ""
    @State private var error: String?
    @State private var suggestions: [String] = []
    @State private var busy = false
    private let minPassword = 6

    var body: some View {
        VStack(alignment: .leading, spacing: 16) {
            VStack(alignment: .leading, spacing: 4) {
                Text("Đăng ký").font(.title2.bold())
                Text("Tạo tài khoản để lưu lại các bài đã hỏi.").font(.subheadline).foregroundStyle(.secondary)
            }
            Field(label: "Tên đăng nhập", text: $username, placeholder: "Ví dụ: an.nguyen.7a",
                  contentType: .username, identifier: "username")
            Field(label: "Mật khẩu", text: $password, secure: true, placeholder: "Ít nhất \(minPassword) ký tự",
                  contentType: .newPassword, identifier: "password")
            Field(label: "Nhập lại mật khẩu", text: $confirm, secure: true, contentType: .newPassword,
                  identifier: "confirmPassword")
            FormError(message: error)
            if !suggestions.isEmpty {
                VStack(alignment: .leading, spacing: 8) {
                    Text("Gợi ý tên còn trống (chạm để dùng):").font(.caption).foregroundStyle(.secondary)
                    HStack {
                        ForEach(suggestions, id: \.self) { name in
                            Button(name) {
                                username = name
                                error = nil
                                suggestions = []
                            }
                            .mmGlassButton()
                            .font(.footnote)
                        }
                    }
                }
            }
            Button {
                Task { await submit() }
            } label: {
                Group { if busy { ProgressView() } else { Text("Đăng ký") } }
                    .frame(maxWidth: .infinity, minHeight: 32)
            }
            .mmGlassButton(prominent: true)
            .disabled(busy || username.isEmpty || password.isEmpty)
            .accessibilityIdentifier("registerButton")
            HStack(spacing: 4) {
                Text("Đã có tài khoản?").foregroundStyle(.secondary)
                Button("Đăng nhập", action: onLogin).accessibilityIdentifier("showLogin")
            }
            .font(.subheadline)
            .frame(maxWidth: .infinity)
        }
    }

    private func submit() async {
        guard !busy else { return }
        suggestions = []
        // The same checks as the web, before the request.
        if password.count < minPassword {
            error = "Mật khẩu phải có ít nhất \(minPassword) ký tự."
            return
        }
        if password != confirm {
            error = "Hai lần nhập mật khẩu không khớp."
            return
        }
        busy = true
        defer { busy = false }
        do {
            try await session.register(username: username, password: password)
        } catch let failure as APIError {
            error = failure.message
            suggestions = failure.suggestions
            Haptics.warning()
        } catch {
            self.error = error.localizedDescription
        }
    }
}
