import SwiftUI

/// A tutor reply: Markdown text with $inline$ formulas that wrap with the words, and $$display$$
/// formulas on their own lines (scrolling sideways when wider than the screen).
struct MathText: View {
    let text: String
    @Environment(\.colorScheme) private var colorScheme
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    var body: some View {
        let fontSize = UIFontMetrics(forTextStyle: .body).scaledValue(for: 17)
        let color: UIColor = colorScheme == .dark ? .white : .black
        VStack(alignment: .leading, spacing: 10) {
            ForEach(Array(MathSegments.blocks(text).enumerated()), id: \.offset) { _, block in
                switch block {
                case .paragraph(let pieces):
                    paragraph(pieces, fontSize: fontSize, color: color)
                case .display(let latex):
                    ScrollView(.horizontal, showsIndicators: false) {
                        formula(latex, fontSize: fontSize * 1.1, color: color, display: true)
                    }
                    .frame(maxWidth: .infinity, alignment: .center)
                }
            }
        }
    }

    private func paragraph(_ pieces: [MathSegments.Piece], fontSize: CGFloat, color: UIColor) -> Text {
        pieces.reduce(Text(verbatim: "")) { line, piece in
            switch piece {
            case .text(let markdown):
                let styled = (try? AttributedString(
                    markdown: markdown,
                    options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace)))
                    ?? AttributedString(markdown)
                return Text("\(line)\(Text(styled))")
            case .math(let latex):
                guard let math = MathRenderer.render(latex, fontSize: fontSize, color: color) else {
                    return Text("\(line)\(Text(verbatim: "$\(latex)$").font(.body.monospaced()))")
                }
                let image = Text(Image(uiImage: math.image)).baselineOffset(-math.descent)
                return Text("\(line)\(image)")
            }
        }
    }

    @ViewBuilder
    private func formula(_ latex: String, fontSize: CGFloat, color: UIColor, display: Bool) -> some View {
        if let math = MathRenderer.render(latex, fontSize: fontSize, color: color, display: display) {
            Image(uiImage: math.image)
                .accessibilityLabel(latex)
        } else {
            Text(verbatim: latex).font(.body.monospaced())
        }
    }
}

/// Splits normalized message text (see web/src/lib/math.ts) into paragraphs and formulas.
enum MathSegments {
    enum Piece: Equatable { case text(String), math(String) }
    enum Block: Equatable { case paragraph([Piece]), display(String) }

    static func blocks(_ text: String) -> [Block] {
        var blocks: [Block] = []
        var rest = Substring(text)
        while let open = rest.range(of: "$$") {
            appendParagraphs(rest[..<open.lowerBound], to: &blocks)
            let after = rest[open.upperBound...]
            guard let close = after.range(of: "$$") else {
                appendParagraphs(rest[open.lowerBound...], to: &blocks)
                return blocks
            }
            blocks.append(.display(after[..<close.lowerBound].trimmingCharacters(in: .whitespacesAndNewlines)))
            rest = after[close.upperBound...]
        }
        appendParagraphs(rest, to: &blocks)
        return blocks
    }

    private static func appendParagraphs(_ text: Substring, to blocks: inout [Block]) {
        for paragraph in text.components(separatedBy: "\n\n") {
            let trimmed = paragraph.trimmingCharacters(in: .whitespacesAndNewlines)
            if !trimmed.isEmpty { blocks.append(.paragraph(pieces(trimmed))) }
        }
    }

    /// `$…$` with no space right inside the opening sign is a formula (as in remark-math);
    /// an unclosed `$` (a reply still streaming) stays text.
    static func pieces(_ text: String) -> [Piece] {
        var pieces: [Piece] = []
        var buffer = ""
        var index = text.startIndex
        while index < text.endIndex {
            let ch = text[index]
            if ch == "$", let close = text[text.index(after: index)...].firstIndex(where: { $0 == "$" || $0 == "\n" }),
               text[close] == "$", close > text.index(after: index),
               !text[text.index(after: index)].isWhitespace {
                if !buffer.isEmpty { pieces.append(.text(buffer)); buffer = "" }
                pieces.append(.math(String(text[text.index(after: index)..<close])))
                index = text.index(after: close)
            } else {
                buffer.append(ch)
                index = text.index(after: index)
            }
        }
        if !buffer.isEmpty { pieces.append(.text(buffer)) }
        return pieces
    }
}

extension View {
    /// Liquid Glass on iOS 26, a material on older systems.
    @ViewBuilder
    func mmGlass<S: Shape>(in shape: S, interactive: Bool = false) -> some View {
        if #available(iOS 26, *) {
            glassEffect(interactive ? .regular.interactive() : .regular, in: shape)
        } else {
            background(.ultraThinMaterial, in: shape)
        }
    }
}

struct InlineScreen: View {
    static let reply = """
    Em xét tam giác **ABC** vuông tại $A$ có $AB = 3$, $AC = 4$. Theo định lý Pythagore, \
    $BC^2 = AB^2 + AC^2$ nên $BC = \\sqrt{3^2 + 4^2} = 5$.

    Đường cao $AH$ thỏa mãn hệ thức:

    $$AH = \\dfrac{AB \\cdot AC}{BC} = \\dfrac{3 \\cdot 4}{5} = 2,4$$

    Góc $\\widehat{ABC}$ có $\\sin \\widehat{ABC} = \\dfrac{AC}{BC} = \\dfrac{4}{5}$, còn cung \
    $\\overset{\\frown}{AB}$ và $\\triangle ABC \\backsim \\triangle HBA$. Hệ phương trình \
    $\\begin{cases} x + y = 3 \\\\ x - y = 1 \\end{cases}$ cho $x = 2$.

    $$\\int_0^1 \\left(x^2 + \\frac{1}{x + 1}\\right) dx = \\frac{1}{3} + \\ln 2 \\approx 1,0265$$

    Vậy $S_{\\text{đáy}} = 12\\text{ cm}^2$. Em thử tính $\\overrightarrow{AB} \\cdot \\overrightarrow{AC}$ \
    rồi cho thầy biết kết quả nhé? Còn $x$ chưa đóng: $x + 1
    """

    var body: some View {
        ScrollView {
            MathText(text: Self.reply)
                .padding(16)
                .padding(.bottom, 80)
        }
        .overlay(alignment: .bottom) {
            HStack(spacing: 12) {
                Text("Nhập câu trả lời…").foregroundStyle(.secondary)
                Spacer()
                Image(systemName: "arrow.up.circle.fill").font(.title2).foregroundStyle(.blue)
            }
            .padding(.horizontal, 16).padding(.vertical, 12)
            .mmGlass(in: .rect(cornerRadius: 24))
            .padding(.horizontal, 12).padding(.bottom, 8)
        }
    }
}
