import SwiftUI

/// One key of the math keyboard.
struct MathKey: Identifiable, Hashable {
    enum Action: Hashable {
        /// Keys for MTMathEditor.insert, in order.
        case keys([String])
        /// A gallery-style template (`#?` slots, `#@` the term before the caret).
        case template(String)
    }

    let id: String
    /// What the key shows: LaTeX drawn with SwiftMath, or plain text when `text` is set.
    let label: String
    let text: Bool
    /// Read by VoiceOver.
    let spoken: String
    let action: Action

    static func latex(_ id: String, _ label: String, _ spoken: String, _ action: Action) -> MathKey {
        MathKey(id: id, label: label, text: false, spoken: spoken, action: action)
    }

    static func plain(_ character: String, spoken: String? = nil) -> MathKey {
        MathKey(id: character, label: character, text: true, spoken: spoken ?? character, action: .keys([character]))
    }
}

/// The on-screen keyboard of the formula editor (web: MathLive's virtual keyboard), with four
/// pages and the formula gallery.
struct MathKeyboard: View {
    enum Page: String, CaseIterable, Identifiable {
        case numbers = "123", letters = "abc", geometry = "Hình", functions = "f(x)", gallery = "Mẫu"
        var id: String { rawValue }
    }

    let model: FormulaEditorModel
    @State private var page: Page = .numbers
    @State private var uppercase = true

    var body: some View {
        VStack(spacing: 8) {
            switch page {
            case .numbers: grid(Self.numbers)
            case .letters: letters
            case .geometry: grid(Self.geometry)
            case .functions: grid(Self.functions)
            case .gallery: TemplateGallery { model.template($0) }.frame(height: 232)
            }
            HStack(spacing: 6) {
                ForEach(Page.allCases) { item in
                    // Plain style: the default one tints the label blue, over the blue background.
                    Button(item.rawValue) { page = item }
                        .buttonStyle(.plain)
                        .font(.footnote.weight(.semibold))
                        .frame(minWidth: 40, minHeight: 34)
                        .foregroundStyle(page == item ? Color.white : .primary)
                        .background(page == item ? Brand.primary : Color(.tertiarySystemFill), in: .rect(cornerRadius: 8))
                        .accessibilityIdentifier("page-\(item.rawValue)")
                }
                Spacer(minLength: 4)
                control("arrow.left", spoken: "Sang trái", id: "key-left") { model.left() }
                control("arrow.right", spoken: "Sang phải", id: "key-right") { model.right() }
                control("delete.left", spoken: "Xóa", id: "key-backspace") { model.backspace() }
            }
        }
        .padding(10)
        .background(Color(.secondarySystemBackground))
    }

    private func grid(_ rows: [[MathKey]]) -> some View {
        VStack(spacing: 6) {
            ForEach(rows.indices, id: \.self) { row in
                HStack(spacing: 6) {
                    ForEach(rows[row]) { key in KeyButton(key: key) { press(key) } }
                }
            }
        }
        .frame(height: 232)
    }

    private var letters: some View {
        let rows = ["QWERTYUIOP", "ASDFGHJKL", "ZXCVBNM"].map { row in
            row.map { MathKey.plain(uppercase ? String($0) : String($0).lowercased()) }
        }
        return VStack(spacing: 6) {
            ForEach(rows.indices, id: \.self) { row in
                HStack(spacing: 5) {
                    if row == 2 {
                        Button { uppercase.toggle() } label: {
                            Image(systemName: uppercase ? "shift.fill" : "shift").frame(maxWidth: .infinity, maxHeight: .infinity)
                        }
                        .buttonStyle(.plain)
                        .background(Color(.tertiarySystemFill), in: .rect(cornerRadius: 8))
                        .accessibilityLabel(uppercase ? "Chữ thường" : "Chữ hoa")
                        .accessibilityIdentifier("key-shift")
                    }
                    ForEach(rows[row]) { key in KeyButton(key: key) { press(key) } }
                }
            }
            HStack(spacing: 6) {
                ForEach([MathKey.plain(","), .plain("'", spoken: "phẩy trên"), .plain("("), .plain(")"), .plain("|")]) { key in
                    KeyButton(key: key) { press(key) }
                }
            }
        }
        .frame(height: 232)
    }

    private func control(_ systemImage: String, spoken: String, id: String, action: @escaping () -> Void) -> some View {
        Button(action: action) {
            Image(systemName: systemImage).frame(width: 44, height: 34)
        }
        .buttonStyle(.plain)
        .background(Color(.tertiarySystemFill), in: .rect(cornerRadius: 8))
        .accessibilityLabel(spoken)
        .accessibilityIdentifier(id)
    }

    private func press(_ key: MathKey) {
        switch key.action {
        case .keys(let keys): for input in keys { model.key(input) }
        case .template(let template): model.template(template)
        }
    }

    // MARK: Pages

    static let numbers: [[MathKey]] = [
        [.plain("7"), .plain("8"), .plain("9"), .plain("÷", spoken: "chia"),
         .latex("frac", "\\frac{\\square}{\\square}", "phân số", .keys(["/"]))],
        [.plain("4"), .plain("5"), .plain("6"), .plain("×", spoken: "nhân"),
         .latex("square", "\\square^{2}", "bình phương", .template("#@^{2}"))],
        [.plain("1"), .plain("2"), .plain("3"), .plain("−", spoken: "trừ").with(action: .keys(["-"])),
         .latex("power", "\\square^{\\square}", "lũy thừa", .keys(["^"]))],
        [.plain("0"), .plain(","), .plain("="), .plain("+", spoken: "cộng"),
         .latex("sqrt", "\\sqrt{\\square}", "căn bậc hai", .keys(["\\sqrt"]))],
        [.plain("x"), .plain("y"), .plain("("), .plain(")"),
         .latex("subscript", "\\square_{\\square}", "chỉ số dưới", .keys(["_"]))],
    ]

    static let geometry: [[MathKey]] = [
        [.latex("angle", "\\angle", "góc", .keys(["\\angle"])), .latex("triangle", "\\triangle", "tam giác", .keys(["\\triangle"])),
         .latex("perp", "\\perp", "vuông góc", .keys(["\\perp"])), .latex("parallel", "\\parallel", "song song", .keys(["\\parallel"])),
         .latex("similar", "\\backsim", "đồng dạng", .keys(["\\backsim"]))],
        [.latex("hat", "\\widehat{\\square}", "góc (mũ)", .template("\\widehat{#?}")),
         .latex("segment", "\\overline{\\square}", "đoạn thẳng", .template("\\overline{#?}")),
         .latex("vector", "\\overrightarrow{\\square}", "vectơ", .template("\\overrightarrow{#?}")),
         .latex("arc", "\\overset{\\frown}{\\square}", "cung", .template("\\overset{\\frown}{#?}")),
         .latex("degree", "\\square^{\\circ}", "độ", .keys(["^", "\\circ", "^"]))],
        [.latex("pi", "\\pi", "pi", .keys(["\\pi"])), .latex("cong", "=", "bằng", .keys(["="])),
         .latex("ne", "\\ne", "khác", .keys(["\\ne"])), .latex("cdot", "\\cdot", "chấm nhân", .keys(["\\cdot"])),
         .latex("nthroot", "\\sqrt[\\square]{\\square}", "căn bậc n", .keys(["\\nthroot"]))],
        [.plain("A"), .plain("B"), .plain("C"), .plain("D"), .plain("O")],
        [.plain("H"), .plain("M"), .plain("N"), .plain("E"), .plain("F")],
    ]

    static let functions: [[MathKey]] = [
        [.latex("sin", "\\sin", "sin", .keys(["\\sin"])), .latex("cos", "\\cos", "cos", .keys(["\\cos"])),
         .latex("tan", "\\tan", "tan", .keys(["\\tan"])), .latex("cot", "\\cot", "cot", .keys(["\\cot"])),
         .latex("log", "\\log_{\\square}", "logarit", .template("\\log_{#?}#?"))],
        [.latex("le", "\\le", "nhỏ hơn hoặc bằng", .keys(["\\le"])), .latex("ge", "\\ge", "lớn hơn hoặc bằng", .keys(["\\ge"])),
         .latex("lt", "<", "nhỏ hơn", .keys(["<"])), .latex("gt", ">", "lớn hơn", .keys([">"])),
         .latex("approx", "\\approx", "xấp xỉ", .keys(["\\approx"]))],
        [.latex("pm", "\\pm", "cộng trừ", .keys(["\\pm"])), .latex("infty", "\\infty", "vô cực", .keys(["\\infty"])),
         .latex("Delta", "\\Delta", "delta", .keys(["\\Delta"])), .latex("alpha", "\\alpha", "alpha", .keys(["\\alpha"])),
         .latex("abs", "|\\square|", "giá trị tuyệt đối", .keys(["||"]))],
        [.latex("in", "\\in", "thuộc", .keys(["\\in"])), .latex("notin", "\\notin", "không thuộc", .keys(["\\notin"])),
         .latex("subset", "\\subset", "tập con", .keys(["\\subset"])), .latex("cup", "\\cup", "hợp", .keys(["\\cup"])),
         .latex("cap", "\\cap", "giao", .keys(["\\cap"]))],
        [.latex("implies", "\\Rightarrow", "suy ra", .keys(["\\Rightarrow"])), .latex("iff", "\\Leftrightarrow", "tương đương", .keys(["\\Leftrightarrow"])),
         .latex("ln", "\\ln", "ln", .keys(["\\ln"])), .latex("int", "\\int", "tích phân", .template("\\int_{#?}^{#?}#?")),
         .latex("sum", "\\sum", "tổng", .template("\\sum_{#?}^{#?}#?"))],
    ]
}

private extension MathKey {
    func with(action: Action) -> MathKey { MathKey(id: id, label: label, text: text, spoken: spoken, action: action) }
}

private struct KeyButton: View {
    let key: MathKey
    let action: () -> Void
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        Button(action: action) {
            Group {
                if key.text {
                    Text(key.label).font(.title3)
                } else if let math = MathRenderer.render(key.label, fontSize: 34,
                                                         color: colorScheme == .dark ? .white : .black) {
                    // As typeset: small symbols stay small; only labels too big for a key shrink.
                    if math.image.size.height > 44 || math.image.size.width > 62 {
                        Image(uiImage: math.image).resizable().scaledToFit().frame(maxWidth: 62, maxHeight: 44)
                    } else {
                        Image(uiImage: math.image)
                    }
                } else {
                    Text(key.spoken).font(.caption)
                }
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .contentShape(.rect)
        }
        .buttonStyle(.plain)
        .background(Color(.systemBackground), in: .rect(cornerRadius: 8))
        .shadow(color: .black.opacity(0.12), radius: 0, y: 1)
        .accessibilityLabel(key.spoken)
        .accessibilityIdentifier("key-\(key.id)")
    }
}

/// The formula gallery (web: the MathLive dialog's tabs), from shared/formula_templates.json.
struct TemplateGallery: View {
    let onPick: (String) -> Void
    @State private var group = SharedData.formulaGroups.first?.id ?? ""

    var body: some View {
        VStack(spacing: 8) {
            ScrollView(.horizontal, showsIndicators: false) {
                HStack(spacing: 6) {
                    ForEach(SharedData.formulaGroups) { item in
                        Button(item.name) { group = item.id }
                            .buttonStyle(.plain)
                            .font(.footnote.weight(.medium))
                            .padding(.horizontal, 10).padding(.vertical, 6)
                            .foregroundStyle(group == item.id ? Color.white : .primary)
                            .background(group == item.id ? Brand.primary : Color(.tertiarySystemFill), in: .capsule)
                    }
                }
            }
            ScrollView {
                let current = SharedData.formulaGroups.first { $0.id == group }
                LazyVGrid(columns: [GridItem(.adaptive(minimum: current?.wide == true ? 160 : 70), spacing: 8)], spacing: 8) {
                    ForEach(current?.items ?? [], id: \.self) { template in
                        Button { onPick(template.latex) } label: { TemplateTile(template: template) }
                            .buttonStyle(.plain)
                            .accessibilityLabel(template.label)
                    }
                }
            }
        }
    }
}

struct TemplateTile: View {
    let template: SharedData.Template
    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        // \square is SwiftMath's empty-slot box.
        let latex = template.latex.replacingOccurrences(of: "#?", with: "\\square ").replacingOccurrences(of: "#@", with: "\\square ")
        Group {
            if let math = MathRenderer.render(latex, fontSize: 18, color: colorScheme == .dark ? .white : .black) {
                Image(uiImage: math.image).resizable().scaledToFit().frame(maxHeight: 34)
            } else {
                Text(template.label).font(.caption)
            }
        }
        .frame(maxWidth: .infinity, minHeight: 50)
        .padding(.horizontal, 6)
        .background(Color(.systemBackground), in: .rect(cornerRadius: 10))
    }
}
