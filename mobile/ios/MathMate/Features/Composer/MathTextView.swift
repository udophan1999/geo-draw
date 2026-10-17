import SwiftUI
import UIKit

/// The message box: text with formula chips (web: components/chat/useMathEditor.tsx).
/// - `$…$` typed or pasted becomes a chip; one Backspace right after gives the source back.
/// - A tap on a chip opens it in the formula editor.
/// - A pasted image becomes the attachment.
/// - Hardware keyboard: Return sends, Shift+Return breaks the line.
@MainActor
final class MathTextView: UITextView {
    var onChange: ((String) -> Void)?
    var onSubmit: (() -> Void)?
    var onImage: ((Data) -> Void)?
    /// A chip was tapped: its LaTeX and its range in the text.
    var onOpenFormula: ((String, NSRange) -> Void)?

    /// The chip that `$…$` just became: one Backspace right away gives the source back.
    private var justConverted: (location: Int, latex: String)?
    private let placeholderLabel = UILabel()

    var placeholder = "" {
        didSet { placeholderLabel.text = placeholder }
    }

    var bodyFont: UIFont { UIFont.preferredFont(forTextStyle: .body) }

    init() {
        super.init(frame: .zero, textContainer: nil)
        font = bodyFont
        adjustsFontForContentSizeCategory = true
        backgroundColor = .clear
        textContainerInset = UIEdgeInsets(top: 8, left: 0, bottom: 8, right: 0)
        textContainer.lineFragmentPadding = 0
        typingAttributes = [.font: bodyFont, .foregroundColor: UIColor.label]
        placeholderLabel.font = bodyFont
        placeholderLabel.adjustsFontForContentSizeCategory = true
        placeholderLabel.textColor = .placeholderText
        placeholderLabel.numberOfLines = 1
        placeholderLabel.isAccessibilityElement = false
        addSubview(placeholderLabel)
        registerForTraitChanges([UITraitUserInterfaceStyle.self]) { (view: MathTextView, _) in view.redrawChips() }
    }

    required init?(coder: NSCoder) { fatalError("not used") }

    override func layoutSubviews() {
        super.layoutSubviews()
        placeholderLabel.frame = CGRect(x: textContainerInset.left, y: textContainerInset.top,
                                        width: bounds.width, height: bodyFont.lineHeight)
    }

    // MARK: Content

    /// The message: text with `$latex$` for every chip.
    var messageText: String { MessageTextCodec.messageText(from: textStorage) }

    var isEmpty: Bool { textStorage.length == 0 }

    func plain(_ text: String) -> NSAttributedString {
        NSAttributedString(string: text, attributes: [.font: bodyFont, .foregroundColor: UIColor.label])
    }

    func chip(_ latex: String) -> NSAttributedString {
        let chip = NSMutableAttributedString(attachment: FormulaAttachment(latex: latex, font: bodyFont, traits: traitCollection))
        chip.addAttributes([.font: bodyFont], range: NSRange(location: 0, length: chip.length))
        return chip
    }

    private func content(_ pieces: [MessageTextCodec.Piece]) -> NSAttributedString {
        let out = NSMutableAttributedString()
        for piece in pieces {
            switch piece {
            case .text(let text): out.append(plain(text))
            case .formula(let latex): out.append(chip(latex))
            }
        }
        return out
    }

    /// Load a stored message (editing it): `$latex$` back to chips.
    func load(_ message: String) {
        textStorage.setAttributedString(content(MessageTextCodec.pieces(ofMessage: message)))
        selectedRange = NSRange(location: textStorage.length, length: 0)
        changed()
    }

    func clear() {
        textStorage.setAttributedString(NSAttributedString())
        justConverted = nil
        changed()
    }

    /// Put text at the caret (the symbol bar) and keep typing after it.
    func insert(_ snippet: String) {
        replace(selectedRange, with: plain(snippet))
    }

    /// A formula from the editor: plain Unicode when it can be (`BC²`), else a chip, kept apart
    /// from the words around it by spaces.
    func insertFormula(_ latex: String) {
        let string = textStorage.string as NSString
        let range = selectedRange
        let before = range.location > 0 ? string.substring(with: NSRange(location: range.location - 1, length: 1)) : ""
        let after = range.upperBound < string.length ? string.substring(with: NSRange(location: range.upperBound, length: 1)) : ""
        let out = NSMutableAttributedString()
        if !before.isEmpty && before.rangeOfCharacter(from: .whitespacesAndNewlines) == nil { out.append(plain(" ")) }
        if let plainText = LatexToPlain.plain(latex) { out.append(plain(plainText)) } else { out.append(chip(latex)) }
        if after.rangeOfCharacter(from: .whitespacesAndNewlines) == nil { out.append(plain(" ")) }
        replace(range, with: out)
    }

    /// An edited chip (from the formula editor).
    func replaceFormula(at range: NSRange, with latex: String) {
        guard range.upperBound <= textStorage.length else { return }
        replace(range, with: chip(latex))
    }

    private func replace(_ range: NSRange, with content: NSAttributedString) {
        textStorage.replaceCharacters(in: range, with: content)
        selectedRange = NSRange(location: range.location + content.length, length: 0)
        justConverted = nil
        changed()
        scrollRangeToVisible(selectedRange)
    }

    func changed() {
        placeholderLabel.isHidden = !isEmpty
        accessibilityValue = messageText
        typingAttributes = [.font: bodyFont, .foregroundColor: UIColor.label]
        onChange?(messageText)
    }

    /// Chips are images: draw them again in the new colours (light ↔ dark).
    private func redrawChips() {
        let chips = NSMutableArray()
        textStorage.enumerateAttribute(.attachment, in: NSRange(location: 0, length: textStorage.length)) { value, range, _ in
            if let formula = value as? FormulaAttachment { chips.add((range, formula.latex)) }
        }
        let selection = selectedRange
        for case let (range, latex) as (NSRange, String) in chips.reversed() {
            textStorage.replaceCharacters(in: range, with: chip(latex))
        }
        selectedRange = selection
    }

    // MARK: Typing rules

    /// After typing: a `$…$` just closed before the caret becomes a chip.
    func applyTypedRule() {
        let caret = selectedRange.location
        let string = textStorage.string as NSString
        let lineStart = string.lineRange(for: NSRange(location: caret, length: 0)).location
        let before = string.substring(with: NSRange(location: lineStart, length: caret - lineStart))
        guard let match = MessageTextCodec.typedFormula.firstMatch(
            in: before, range: NSRange(location: 0, length: (before as NSString).length)) else { return }
        let start = lineStart + match.range(at: 1).upperBound
        let latex = (before as NSString).substring(with: match.range(at: 2))
        textStorage.replaceCharacters(in: NSRange(location: start, length: caret - start), with: chip(latex))
        selectedRange = NSRange(location: start + 1, length: 0)
        justConverted = (start, latex)
    }

    /// Backspace right after a conversion: the chip becomes `$latex$` text again.
    /// Returns false when it handled the deletion.
    func handleBackspace(in range: NSRange) -> Bool {
        defer { justConverted = nil }
        guard let converted = justConverted, range.length == 1, range.location == converted.location else { return true }
        let source = "$\(converted.latex)$"
        textStorage.replaceCharacters(in: range, with: plain(source))
        selectedRange = NSRange(location: range.location + (source as NSString).length, length: 0)
        changed()
        return false
    }

    func forgetConversion() { justConverted = nil }

    // MARK: Paste

    override func canPerformAction(_ action: Selector, withSender sender: Any?) -> Bool {
        if action == #selector(paste(_:)) && UIPasteboard.general.hasImages && onImage != nil { return true }
        return super.canPerformAction(action, withSender: sender)
    }

    override func paste(_ sender: Any?) {
        let board = UIPasteboard.general
        if board.hasImages, !board.hasStrings, let image = board.image, let data = image.pngData() {
            onImage?(data)
            return
        }
        guard let text = board.string, text.contains("$") else { return super.paste(sender) }
        replace(selectedRange, with: content(MessageTextCodec.pieces(ofPasted: text)))
    }

    // MARK: Hardware keyboard

    override var keyCommands: [UIKeyCommand]? {
        let send = UIKeyCommand(input: "\r", modifierFlags: [], action: #selector(submitFromKeyboard))
        send.wantsPriorityOverSystemBehavior = true
        let newLine = UIKeyCommand(input: "\r", modifierFlags: .shift, action: #selector(newLineFromKeyboard))
        newLine.wantsPriorityOverSystemBehavior = true
        return [send, newLine]
    }

    @objc private func submitFromKeyboard() {
        // A Vietnamese input method may still be composing: let Return finish the word.
        if markedTextRange != nil { unmarkText(); return }
        onSubmit?()
    }

    @objc private func newLineFromKeyboard() {
        insertText("\n")
    }
}

/// Lets SwiftUI drive the message box (insert a symbol or formula, clear it, focus it).
@MainActor
@Observable
final class ComposerController {
    fileprivate(set) weak var view: MathTextView?
    private(set) var text = ""
    var isEmpty: Bool { text.isEmpty }

    func insert(_ snippet: String) { view?.insert(snippet); view?.becomeFirstResponder() }
    func insertFormula(_ latex: String) { view?.insertFormula(latex); view?.becomeFirstResponder() }
    func replaceFormula(at range: NSRange, with latex: String) { view?.replaceFormula(at: range, with: latex) }
    func clear() { view?.clear() }
    func load(_ message: String) { view?.load(message) }
    func focus() { view?.becomeFirstResponder() }

    fileprivate func update(_ text: String) { if self.text != text { self.text = text } }
}

/// The message box in SwiftUI: grows with its text up to `maxHeight`, then scrolls.
struct ComposerField: UIViewRepresentable {
    let controller: ComposerController
    var placeholder: String
    var initialText = ""
    var autofocus = false
    var maxHeight: CGFloat = 150
    var identifier = "composer"
    var onSubmit: () -> Void = {}
    var onImage: (Data) -> Void = { _ in }
    var onOpenFormula: (String, NSRange) -> Void = { _, _ in }

    func makeUIView(context: Context) -> MathTextView {
        let view = MathTextView()
        view.delegate = context.coordinator
        view.accessibilityIdentifier = identifier
        view.setContentCompressionResistancePriority(.defaultLow, for: .horizontal)
        controller.view = view
        view.onChange = { [weak controller] text in controller?.update(text) }
        view.load(initialText)
        if autofocus { DispatchQueue.main.async { view.becomeFirstResponder() } }
        return view
    }

    func updateUIView(_ view: MathTextView, context: Context) {
        view.placeholder = placeholder
        view.onSubmit = onSubmit
        view.onImage = onImage
        view.onOpenFormula = onOpenFormula
        controller.view = view
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: MathTextView, context: Context) -> CGSize? {
        let width = proposal.width ?? 300
        let fitting = uiView.sizeThatFits(CGSize(width: width, height: .greatestFiniteMagnitude)).height
        uiView.isScrollEnabled = fitting > maxHeight
        return CGSize(width: width, height: min(max(fitting, uiView.bodyFont.lineHeight + 16), maxHeight))
    }

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
            if !deleting && view.markedTextRange == nil { view.applyTypedRule() }
            view.changed()
            view.invalidateIntrinsicContentSize()
        }

        func textView(_ textView: UITextView, primaryActionFor textItem: UITextItem, defaultAction: UIAction) -> UIAction? {
            guard case .textAttachment(let attachment) = textItem.content,
                  let formula = attachment as? FormulaAttachment,
                  let view = textView as? MathTextView else { return defaultAction }
            let range = textItem.range
            return UIAction { _ in view.onOpenFormula?(formula.latex, range) }
        }
    }
}
