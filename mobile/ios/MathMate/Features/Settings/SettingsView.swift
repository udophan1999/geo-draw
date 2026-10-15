import SwiftUI

/// Drawing settings, the THCS drawing conventions and the account (web: SettingsDialog).
struct SettingsView: View {
    @Environment(SessionStore.self) private var session
    @Environment(\.dismiss) private var dismiss
    @State private var draft: DrawSettings?
    @State private var help: String?
    @State private var error: String?
    @State private var saving = false
    @State private var deleting = false

    private static let qualityLabels: [DrawSettings.Quality: String] = [
        .l: "Thấp — nhanh nhất", .m: "Vừa", .h: "Cao — chậm hơn",
    ]

    var body: some View {
        NavigationStack {
            Form {
                if let draft = Binding($draft) {
                    drawingSection(draft)
                } else {
                    Section { ProgressView().frame(maxWidth: .infinity) }
                }
                if let help {
                    Section {
                        DisclosureGroup("Quy ước hình học THCS") {
                            Text(markdown(help)).font(.callout)
                        }
                    }
                }
                if let user = session.user {
                    Section("Tài khoản") {
                        LabeledContent("Tên đăng nhập", value: user.name)
                        if let quota = session.me?.quota {
                            LabeledContent("Lượt AI hôm nay", value: "\(quota.used)/\(quota.limit)")
                        }
                        Button("Đăng xuất", role: .destructive) {
                            dismiss()
                            Task { await session.logout() }
                        }
                    }
                    Section {
                        Button("Xóa tài khoản…", role: .destructive) { deleting = true }
                            .accessibilityIdentifier("deleteAccount")
                    } footer: {
                        Text("Xóa vĩnh viễn tài khoản và mọi dữ liệu.")
                    }
                }
                if let error {
                    Section { Text(error).foregroundStyle(.red) }
                }
            }
            .navigationTitle("Cài đặt")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) { Button("Hủy") { dismiss() } }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Lưu") { Task { await save() } }
                        .disabled(draft == nil || saving)
                }
            }
            .sheet(isPresented: $deleting) { DeleteAccountView() }
            .task { await load() }
        }
    }

    @ViewBuilder
    private func drawingSection(_ draft: Binding<DrawSettings>) -> some View {
        let aiAvailable = session.me?.aiAvailable ?? true
        Section {
            Picker("Cách vẽ hình", selection: draft.mode) {
                Text("\(Brand.appName) AI").tag(DrawSettings.Mode.ai)
                Text("Parser nhanh").tag(DrawSettings.Mode.parser)
            }
            .pickerStyle(.inline)
            .labelsHidden()
            .disabled(!aiAvailable)
        } header: {
            Text("Cách vẽ hình")
        } footer: {
            if !aiAvailable {
                Text("Máy chủ chưa cấu hình khóa AI.")
            } else if draft.wrappedValue.mode == .ai {
                Text("Vẽ được đề phức tạp. Mỗi lần vẽ tốn 1 lượt AI.")
            } else {
                Text("Chạy trên máy chủ, không tốn lượt AI; chỉ hiểu các mẫu cơ bản.")
            }
        }
        Section {
            if draft.wrappedValue.mode == .ai {
                Picker("Mô hình AI", selection: draft.model) {
                    Text("Nhanh — hợp đa số đề").tag(DrawSettings.Model.flash)
                    Text("Chuyên sâu — ưu tiên chất lượng").tag(DrawSettings.Model.pro)
                }
            }
            Picker("Chất lượng hình", selection: draft.quality) {
                ForEach(DrawSettings.Quality.allCases, id: \.self) { quality in
                    Text(Self.qualityLabels[quality] ?? quality.rawValue).tag(quality)
                }
            }
            Toggle("Video hoạt hình", isOn: draft.animate)
        } footer: {
            Text("Gia sư luôn dùng \(Brand.appName) AI; các lựa chọn trên áp dụng cho việc vẽ hình.")
        }
    }

    private func markdown(_ text: String) -> AttributedString {
        (try? AttributedString(markdown: text, options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace)))
            ?? AttributedString(text)
    }

    private func load() async {
        do {
            var settings = try await session.api.settings()
            if session.me?.aiAvailable == false { settings.mode = .parser }
            draft = settings
        } catch {
            self.error = error.localizedDescription
        }
        help = try? await session.api.help()
    }

    private func save() async {
        guard let draft else { return }
        saving = true
        defer { saving = false }
        do {
            _ = try await session.api.saveSettings(draft)
            Haptics.success()
            dismiss()
        } catch {
            self.error = error.localizedDescription
        }
    }
}

/// Delete the account for good, after the password is typed again (web: DeleteAccountDialog).
struct DeleteAccountView: View {
    @Environment(SessionStore.self) private var session
    @Environment(\.dismiss) private var dismiss
    @State private var password = ""
    @State private var error: String?
    @State private var busy = false

    var body: some View {
        NavigationStack {
            Form {
                Section {
                    Text("Mọi cuộc trò chuyện, hình vẽ và cài đặt của bạn sẽ bị xóa vĩnh viễn, không khôi phục được.")
                }
                Section("Nhập mật khẩu để xác nhận") {
                    SecureField("Mật khẩu", text: $password)
                        .textContentType(.password)
                        .accessibilityIdentifier("deletePassword")
                    if let error {
                        Text(error).foregroundStyle(.red).accessibilityIdentifier("deleteError")
                    }
                }
                Section {
                    Button(role: .destructive) {
                        Task { await delete() }
                    } label: {
                        HStack {
                            Text("Xóa vĩnh viễn")
                            if busy { Spacer(); ProgressView() }
                        }
                    }
                    .disabled(password.isEmpty || busy)
                    .accessibilityIdentifier("confirmDelete")
                }
            }
            .navigationTitle("Xóa tài khoản?")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar { ToolbarItem(placement: .cancellationAction) { Button("Hủy") { dismiss() } } }
        }
    }

    private func delete() async {
        busy = true
        defer { busy = false }
        do {
            try await session.deleteAccount(password: password)
            Haptics.success()
        } catch {
            self.error = error.localizedDescription
            password = ""
            Haptics.warning()
        }
    }
}
