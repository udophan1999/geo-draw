import SwiftUI

/// The tutor's levels, in the order of geo_draw/tutor_prompts.py HINT_LEVELS
/// (web: lib/hintLevels.ts).
enum HintLevels {
    static let names = ["Hiểu đề", "Nhớ kiến thức", "Chiến lược", "Bước đầu tiên", "Sâu hơn nữa"]
}

/// Hint or worked solution, the hint level and "Gợi ý sâu hơn" (web: chat/TutorBar.tsx).
struct TutorBar: View {
    let conversation: Conversation
    let busy: Bool
    let onAction: (TutorAction) -> Void
    @State private var confirmSolution = false
    @Namespace private var glass

    private var solution: Bool { conversation.mode == .solution }
    private var level: Int { min(max(conversation.hintLevel, 1), HintLevels.names.count) }

    var body: some View {
        MMGlassContainer(spacing: 8) {
            HStack(spacing: 8) {
                modeSwitch
                Spacer(minLength: 4)
                status
            }
        }
        .confirmationDialog("Xem lời giải chi tiết?", isPresented: $confirmSolution, titleVisibility: .visible) {
            Button("Xem lời giải") { onAction(.solution) }
            Button("Tiếp tục tự làm", role: .cancel) {}
        } message: {
            Text("Tự nghĩ ra lời giải sẽ giúp nhớ lâu hơn. Nếu đã thử mà vẫn bí, hoặc muốn đối chiếu bài làm, hãy xem lời giải đầy đủ. Bạn có thể quay lại chế độ gợi ý bất cứ lúc nào.")
        }
    }

    private var modeSwitch: some View {
        HStack(spacing: 2) {
            modeButton("Gợi ý", systemImage: "lightbulb", active: !solution) {
                if solution { onAction(.hint) }
            }
            modeButton("Lời giải", systemImage: "list.number", active: solution) {
                if !solution { confirmSolution = true }
            }
        }
        .padding(3)
        .mmGlass(in: .capsule)
        .disabled(busy)
        .accessibilityElement(children: .contain)
        .accessibilityLabel("Cách trợ giảng")
    }

    private func modeButton(_ title: String, systemImage: String, active: Bool, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Label(title, systemImage: systemImage)
                .font(.footnote.weight(.semibold))
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .foregroundStyle(active ? Color.primary : .secondary)
                .background {
                    if active {
                        Capsule().fill(Color(.systemBackground)).shadow(color: .black.opacity(0.08), radius: 2, y: 1)
                            .matchedGeometryEffect(id: "mode", in: glass)
                    }
                }
        }
        .buttonStyle(.plain)
        .animation(.snappy, value: solution)
        .accessibilityAddTraits(active ? .isSelected : [])
    }

    @ViewBuilder
    private var status: some View {
        if solution {
            Text("Đang xem lời giải đầy đủ").font(.caption).foregroundStyle(.secondary)
        } else if conversation.solved {
            HStack(spacing: 6) {
                dots(filled: HintLevels.names.count, color: .green)
                Label("Đã giải xong", systemImage: "checkmark.circle.fill")
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.green)
            }
        } else {
            HStack(spacing: 8) {
                VStack(alignment: .trailing, spacing: 3) {
                    dots(filled: level, color: Brand.primary)
                    Text(HintLevels.names[level - 1]).font(.caption2).foregroundStyle(.secondary)
                }
                .accessibilityElement(children: .ignore)
                .accessibilityLabel("Bậc \(level)/\(HintLevels.names.count): \(HintLevels.names[level - 1])")
                Button {
                    Haptics.selection()
                    onAction(.deeper)
                } label: {
                    Label("Sâu hơn", systemImage: "sparkles").font(.footnote.weight(.semibold))
                }
                .mmGlassButton()
                .controlSize(.small)
                .disabled(busy || level >= HintLevels.names.count)
                .accessibilityLabel("Gợi ý sâu hơn")
                .accessibilityIdentifier("deeperHint")
            }
        }
    }

    private func dots(filled: Int, color: Color) -> some View {
        HStack(spacing: 3) {
            ForEach(0..<HintLevels.names.count, id: \.self) { index in
                Capsule()
                    .fill(index < filled ? color : Color.secondary.opacity(0.25))
                    .frame(width: 12, height: 5)
            }
        }
        .animation(.spring, value: filled)
    }
}
