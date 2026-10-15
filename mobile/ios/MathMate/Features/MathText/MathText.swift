import SwiftUI

/// A message: Markdown-ish text with `$inline$` formulas that wrap with the words, and
/// `$$display$$` formulas on their own lines (centered, scrolling sideways when too wide).
/// web: components/MathMarkdown.tsx.
struct MathText: View {
    let text: String
    /// Shown at the end while a reply streams in.
    var cursor = false
    /// The text style; formulas follow its size.
    var style: UIFont.TextStyle = .body
    @Environment(\.colorScheme) private var colorScheme
    @Environment(\.dynamicTypeSize) private var dynamicTypeSize

    var body: some View {
        let font = UIFont.preferredFont(forTextStyle: style)
        let fontSize = font.pointSize
        let color: UIColor = colorScheme == .dark ? .white : .black
        let blocks = MathBlocks.parse(MathNormalizer.normalize(text))
        VStack(alignment: .leading, spacing: 10) {
            ForEach(Array(blocks.enumerated()), id: \.offset) { index, block in
                let last = cursor && index == blocks.count - 1
                switch block {
                case .paragraph(let lines):
                    paragraph(lines, fontSize: fontSize, color: color, cursor: last)
                        .fixedSize(horizontal: false, vertical: true)
                        .frame(maxWidth: .infinity, alignment: .leading)
                case .display(let latex):
                    DisplayFormula(latex: latex, fontSize: fontSize * MathRenderer.scale * 1.05, color: color)
                }
            }
            if cursor, case .display = blocks.last { Text("▍").foregroundStyle(.secondary) }
        }
        .font(Font(font))
        .textSelection(.enabled)
    }

    private func paragraph(_ lines: [MathBlocks.Line], fontSize: CGFloat, color: UIColor, cursor: Bool) -> Text {
        var out = Text(verbatim: "")
        for (index, line) in lines.enumerated() {
            if index > 0 { out = Text("\(out)\n") }
            out = Text("\(out)\(self.line(line, fontSize: fontSize, color: color))")
        }
        return cursor ? Text("\(out)\(Text(" ▍").foregroundStyle(.secondary))") : out
    }

    private func line(_ line: MathBlocks.Line, fontSize: CGFloat, color: UIColor) -> Text {
        var out: Text
        switch line.kind {
        case .bullet: out = Text("•  ")
        case .heading, .plain: out = Text(verbatim: "")
        }
        for piece in line.pieces {
            switch piece {
            case .text(let markdown):
                out = Text("\(out)\(Text(Self.markdown(markdown)))")
            case .math(let latex):
                guard let math = MathRenderer.render(latex, fontSize: fontSize * MathRenderer.scale, color: color) else {
                    out = Text("\(out)\(Text(verbatim: "$\(latex)$").monospaced())")
                    continue
                }
                let image = Text(Image(uiImage: math.image)).baselineOffset(-math.descent)
                out = Text("\(out)\(image)")
            }
        }
        return line.kind == .heading ? out.font(.headline) : out
    }

    private static func markdown(_ text: String) -> AttributedString {
        (try? AttributedString(markdown: text, options: .init(interpretedSyntax: .inlineOnlyPreservingWhitespace)))
            ?? AttributedString(text)
    }
}

/// A display formula: centered when it fits, scrolling sideways when it does not.
private struct DisplayFormula: View {
    let latex: String
    let fontSize: CGFloat
    let color: UIColor

    var body: some View {
        if let math = MathRenderer.render(latex, fontSize: fontSize, color: color, display: true) {
            ScrollView(.horizontal, showsIndicators: false) {
                Image(uiImage: math.image)
                    .containerRelativeFrame(.horizontal) { length, _ in max(length, math.image.size.width) }
            }
            .scrollBounceBehavior(.basedOnSize, axes: .horizontal)
            .accessibilityLabel(latex)
        } else {
            Text(verbatim: "$$\(latex)$$").font(.callout.monospaced()).foregroundStyle(.secondary)
        }
    }
}

/// Splits normalized message text into paragraphs, lines and formulas.
enum MathBlocks {
    enum Piece: Equatable { case text(String), math(String) }
    struct Line: Equatable {
        enum Kind: Equatable { case plain, bullet, heading }
        var kind: Kind
        var pieces: [Piece]
    }
    enum Block: Equatable { case paragraph([Line]), display(String) }

    static func parse(_ text: String) -> [Block] {
        var blocks: [Block] = []
        var rest = Substring(text)
        while let open = rest.range(of: "$$") {
            let after = rest[open.upperBound...]
            guard let close = after.range(of: "$$") else { break }  // unclosed (still streaming): text
            appendParagraphs(rest[..<open.lowerBound], to: &blocks)
            let latex = after[..<close.lowerBound].trimmingCharacters(in: .whitespacesAndNewlines)
            if !latex.isEmpty { blocks.append(.display(latex)) }
            rest = after[close.upperBound...]
        }
        appendParagraphs(rest, to: &blocks)
        return blocks
    }

    private static func appendParagraphs(_ text: Substring, to blocks: inout [Block]) {
        for paragraph in text.components(separatedBy: "\n\n") {
            let lines = paragraph.split(separator: "\n", omittingEmptySubsequences: true)
                .map { $0.trimmingCharacters(in: .whitespaces) }
                .filter { !$0.isEmpty }
                .map(line)
            if !lines.isEmpty { blocks.append(.paragraph(lines)) }
        }
    }

    /// `- item` / `* item` become bullets and `## Title` a heading; numbered lists stay as typed.
    static func line(_ text: String) -> Line {
        if let match = text.firstMatch(of: /^#{1,6}\s+/) {
            return Line(kind: .heading, pieces: pieces(String(text[match.range.upperBound...])))
        }
        if let match = text.firstMatch(of: /^[-*+]\s+/) {
            return Line(kind: .bullet, pieces: pieces(String(text[match.range.upperBound...])))
        }
        return Line(kind: .plain, pieces: pieces(text))
    }

    /// `$…$` with no space right inside the opening sign is a formula (as in remark-math);
    /// a `$` with no closing one on the line stays text.
    static func pieces(_ text: String) -> [Piece] {
        var pieces: [Piece] = []
        var buffer = ""
        var index = text.startIndex
        while index < text.endIndex {
            let next = text.index(after: index)
            if text[index] == "$", next < text.endIndex, !text[next].isWhitespace, text[next] != "$",
               let close = text[next...].firstIndex(of: "$") {
                if !buffer.isEmpty { pieces.append(.text(buffer)); buffer = "" }
                pieces.append(.math(String(text[next..<close])))
                index = text.index(after: close)
            } else {
                buffer.append(text[index])
                index = next
            }
        }
        if !buffer.isEmpty { pieces.append(.text(buffer)) }
        return pieces
    }
}
