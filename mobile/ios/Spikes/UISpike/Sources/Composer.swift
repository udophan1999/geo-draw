import SwiftUI
import UIKit

/// A formula chip in the message box. Its text is U+FFFC; the LaTeX lives here.
final class FormulaAttachment: NSTextAttachment {
    let latex: String

    @MainActor
    init(latex: String, font: UIFont, color: UIColor) {
        self.latex = latex
        super.init(data: nil, ofType: nil)
        let padding = CGSize(width: 3, height: 2)
        if let math = MathRenderer.render(latex, fontSize: font.pointSize, color: color) {
            let size = CGSize(width: math.image.size.width + padding.width * 2,
                              height: math.image.size.height + padding.height * 2)
            image = UIGraphicsImageRenderer(size: size).image { _ in
                UIColor.systemBlue.withAlphaComponent(0.1).setFill()
                UIBezierPath(roundedRect: CGRect(origin: .zero, size: size), cornerRadius: 5).fill()
                math.image.draw(at: CGPoint(x: padding.width, y: padding.height))
            }
            bounds = CGRect(x: 0, y: -math.descent - padding.height, width: size.width, height: size.height)
        } else {
            // Unparsable: show the source, as the web does with KaTeX errors.
            let text = "$\(latex)$" as NSString
            let attributes: [NSAttributedString.Key: Any] = [
                .font: UIFont.monospacedSystemFont(ofSize: font.pointSize * 0.9, weight: .regular),
                .foregroundColor: UIColor.systemRed]
            let size = text.size(withAttributes: attributes)
            image = UIGraphicsImageRenderer(size: size).image { _ in text.draw(at: .zero, withAttributes: attributes) }
            bounds = CGRect(x: 0, y: font.descender, width: size.width, height: size.height)
        }
    }

    required init?(coder: NSCoder) { fatalError("not used") }
}

/// The rules of the web composer (web/src/components/chat/useMathEditor.tsx), on UITextView.
@MainActor
final class MathTextView: UITextView {
    // NSRegularExpression works in UTF-16 offsets, like NSTextStorage.
    static let typedFormula = try! NSRegularExpression(pattern: #"(^|[^$\\\w])\$([^$\s][^$\n]*?)\$$"#)
    static let pastedFormula = try! NSRegularExpression(pattern: #"(^|[^$\\\w])\$([^$\s][^$\n]*?)\$(?!\$)"#)

    var onChange: ((String) -> Void)?
    var onOpenFormula: ((String) -> Void)?
    /// The chip that `$…$` just became: one Backspace right away gives the source back.
    private var justConverted: (location: Int, latex: String)?

    var bodyFont: UIFont { UIFont.preferredFont(forTextStyle: .body) }

    func chip(_ latex: String) -> NSAttributedString {
        let attachment = FormulaAttachment(latex: latex, font: bodyFont, color: .label)
        let chip = NSMutableAttributedString(attachment: attachment)
        chip.addAttributes([.font: bodyFont], range: NSRange(location: 0, length: chip.length))
        return chip
    }

    func plain(_ text: String) -> NSAttributedString {
        NSAttributedString(string: text, attributes: [.font: bodyFont, .foregroundColor: UIColor.label])
    }

    /// Insert a formula at the caret (from the formula editor).
    func insertFormula(_ latex: String) {
        textStorage.replaceCharacters(in: selectedRange, with: chip(latex))
        selectedRange = NSRange(location: selectedRange.location + 1, length: 0)
        justConverted = nil
        changed()
    }

    /// The message: text with `$latex$` for every chip (lib/messageText.ts toMessageText).
    var messageText: String {
        var out = ""
        textStorage.enumerateAttributes(in: NSRange(location: 0, length: textStorage.length)) { attributes, range, _ in
            if let formula = attributes[.attachment] as? FormulaAttachment {
                out += "$\(formula.latex)$"
            } else {
                out += (textStorage.string as NSString).substring(with: range)
                    .replacingOccurrences(of: "\u{FFFC}", with: "")
            }
        }
        return out
    }

    /// Load a message (editing a sent one): `$latex$` back to chips.
    func load(_ message: String) {
        textStorage.setAttributedString(converted(message, rule: Self.pastedFormula))
        changed()
    }

    private func converted(_ text: String, rule: NSRegularExpression) -> NSAttributedString {
        let out = NSMutableAttributedString()
        let ns = text as NSString
        var last = 0
        for match in rule.matches(in: text, range: NSRange(location: 0, length: ns.length)) {
            let formulaStart = match.range(at: 1).upperBound  // after the character before `$`
            out.append(plain(ns.substring(with: NSRange(location: last, length: formulaStart - last))))
            out.append(chip(ns.substring(with: match.range(at: 2))))
            last = match.range.upperBound
        }
        out.append(plain(ns.substring(from: last)))
        return out
    }

    override func paste(_ sender: Any?) {
        guard let text = UIPasteboard.general.string, text.contains("$") else { return super.paste(sender) }
        let pasted = converted(text, rule: Self.pastedFormula)
        textStorage.replaceCharacters(in: selectedRange, with: pasted)
        selectedRange = NSRange(location: selectedRange.location + pasted.length, length: 0)
        justConverted = nil
        changed()
    }

    /// After typing: a `$…$` just closed before the caret becomes a chip.
    func applyTypedRule() {
        let caret = selectedRange.location
        let string = textStorage.string as NSString
        let lineStart = string.lineRange(for: NSRange(location: caret, length: 0)).location
        let before = string.substring(with: NSRange(location: lineStart, length: caret - lineStart))
        guard let match = Self.typedFormula.firstMatch(
            in: before, range: NSRange(location: 0, length: (before as NSString).length)) else { return }
        let start = lineStart + match.range(at: 1).upperBound
        let latex = (before as NSString).substring(with: match.range(at: 2))
        textStorage.replaceCharacters(in: NSRange(location: start, length: caret - start), with: chip(latex))
        selectedRange = NSRange(location: start + 1, length: 0)
        justConverted = (start, latex)
    }

    /// Backspace right after a conversion: the chip becomes `$latex$` text again.
    func handleBackspace(in range: NSRange) -> Bool {
        defer { justConverted = nil }
        guard let converted = justConverted, range.length == 1, range.location == converted.location
        else { return true }
        let source = "$\(converted.latex)$"
        textStorage.replaceCharacters(in: range, with: plain(source))
        selectedRange = NSRange(location: range.location + (source as NSString).length, length: 0)
        changed()
        return false
    }

    func forgetConversion() { justConverted = nil }

    func changed() { onChange?(messageText) }

    // Hardware keyboard: Return sends, Shift+Return breaks the line (as on the web).
    override var keyCommands: [UIKeyCommand]? {
        [UIKeyCommand(input: "\r", modifierFlags: [], action: #selector(send)),
         UIKeyCommand(input: "\r", modifierFlags: .shift, action: #selector(newLine))]
    }
    var onSend: (() -> Void)?
    @objc private func send() { onSend?() }
    @objc private func newLine() { insertText("\n") }
}

struct ComposerField: UIViewRepresentable {
    @Binding var message: String
    @Binding var formulaRequest: String?
    var initial: String = ""

    func makeUIView(context: Context) -> MathTextView {
        let view = MathTextView()
        view.font = view.bodyFont
        view.adjustsFontForContentSizeCategory = true
        view.backgroundColor = .clear
        view.isScrollEnabled = true
        view.delegate = context.coordinator
        view.onChange = { text in DispatchQueue.main.async { message = text } }
        view.onOpenFormula = { latex in DispatchQueue.main.async { formulaRequest = latex } }
        view.accessibilityIdentifier = "composer"
        view.load(initial)
        return view
    }

    func updateUIView(_ view: MathTextView, context: Context) {}

    func makeCoordinator() -> Coordinator { Coordinator() }

    @MainActor
    final class Coordinator: NSObject, UITextViewDelegate {
        private var deleting = false

        func textView(_ textView: UITextView, shouldChangeTextIn range: NSRange, replacementText text: String) -> Bool {
            guard let view = textView as? MathTextView else { return true }
            deleting = text.isEmpty
            if text.isEmpty { return view.handleBackspace(in: range) }
            view.forgetConversion()
            return true
        }

        func textViewDidChange(_ textView: UITextView) {
            guard let view = textView as? MathTextView else { return }
            if !deleting { view.applyTypedRule() }
            view.changed()
        }

        /// A tap on a chip opens it in the formula editor.
        func textView(_ textView: UITextView, primaryActionFor textItem: UITextItem,
                      defaultAction: UIAction) -> UIAction? {
            guard case .textAttachment(let attachment) = textItem.content,
                  let formula = attachment as? FormulaAttachment,
                  let view = textView as? MathTextView else { return defaultAction }
            return UIAction { _ in view.onOpenFormula?(formula.latex) }
        }
    }
}

struct ComposerScreen: View {
    @State private var message = ""
    @State private var formulaRequest: String?
    var initial = "Cho $\\triangle ABC$ có $AB = 3$ và $\\widehat{A} = 90^\\circ$. Tính $BC$."

    var body: some View {
        VStack(alignment: .leading, spacing: 12) {
            Text("Ô soạn tin").font(.headline)
            ComposerField(message: $message, formulaRequest: $formulaRequest, initial: initial)
                .frame(height: 140)
                .padding(8)
                .mmGlass(in: .rect(cornerRadius: 20))
            Text("Văn bản gửi đi").font(.headline)
            Text(verbatim: message)
                .font(.callout.monospaced())
                .accessibilityIdentifier("messageText")
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(8)
                .background(.quaternary, in: .rect(cornerRadius: 8))
            Spacer()
        }
        .padding(16)
        .alert("Sửa công thức", isPresented: .constant(formulaRequest != nil)) {
            Button("Đóng") { formulaRequest = nil }
        } message: {
            Text(verbatim: formulaRequest ?? "")
        }
    }
}
