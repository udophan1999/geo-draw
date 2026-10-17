import SwiftMath
import SwiftUI
import UIKit

/// The formula being edited, shared by the view that draws it and the math keyboard.
@MainActor
@Observable
final class FormulaEditorModel {
    private(set) var editor: MTMathEditor
    /// Bumped on every change, so the view draws again.
    private(set) var version = 0

    init?(latex: String) {
        guard let editor = MTMathEditor(latex: latex) else { return nil }
        self.editor = editor
    }

    // Read through `version`: MTMathEditor is not observable, so views reading these (the
    // "Chèn" button) would otherwise never update.
    var latex: String { _ = version; return editor.latex }
    var isEmpty: Bool { _ = version; return editor.isEmpty }

    func key(_ input: String) { editor.insert(input); changed() }
    func template(_ latex: String) { editor.insertTemplate(latex); changed() }
    func backspace() { editor.deleteBackward(); changed() }
    func left() { editor.moveLeft(); changed() }
    func right() { editor.moveRight(); changed() }
    func moveCaret(to index: MTMathListIndex) { editor.moveCaret(to: index); changed() }

    private func changed() {
        version += 1
        Haptics.selection()
    }
}

/// Draws the formula with the caret; a tap moves the caret there. A hardware keyboard types
/// into it too (letters, digits, Backspace, ← →).
final class FormulaCanvas: UIView, UIKeyInput {
    var model: FormulaEditorModel?
    private var display: MTMathListDisplay?
    private let caretView = UIView()
    private let hint = UILabel()
    private let fontSize: CGFloat = 30
    private let inset: CGFloat = 16

    override init(frame: CGRect) {
        super.init(frame: frame)
        backgroundColor = .clear
        isAccessibilityElement = true
        accessibilityIdentifier = "formulaEditor"
        accessibilityLabel = "Công thức"
        caretView.backgroundColor = .tintColor
        addSubview(caretView)
        hint.text = "Gõ công thức bằng bàn phím bên dưới"
        hint.font = .preferredFont(forTextStyle: .footnote)
        hint.textColor = .secondaryLabel
        hint.isAccessibilityElement = false
        addSubview(hint)
        addGestureRecognizer(UITapGestureRecognizer(target: self, action: #selector(tapped)))
        registerForTraitChanges([UITraitUserInterfaceStyle.self]) { (view: FormulaCanvas, _) in view.refresh() }
    }

    required init?(coder: NSCoder) { fatalError("not used") }

    /// Typesets the formula again and moves the caret.
    @MainActor
    func refresh() {
        guard let model else { return }
        display = MTTypesetter.createLineForMathList(model.editor.mathList, font: MathRenderer.font(size: fontSize), style: .display)
        accessibilityValue = model.latex
        invalidateIntrinsicContentSize()
        setNeedsDisplay()
        setNeedsLayout()
        blink()
    }

    override var intrinsicContentSize: CGSize {
        let width = (display?.width ?? 0) + inset * 2
        let height = max((display?.ascent ?? 0) + (display?.descent ?? 0), fontSize * 1.4) + inset * 2
        return CGSize(width: width, height: height)
    }

    /// The baseline origin in view coordinates (y down): centered vertically, left-aligned.
    private var origin: CGPoint {
        let ascent = display?.ascent ?? fontSize * 0.8
        let descent = display?.descent ?? fontSize * 0.2
        return CGPoint(x: inset, y: (bounds.height + ascent - descent) / 2)
    }

    override func draw(_ rect: CGRect) {
        guard let display, let context = UIGraphicsGetCurrentContext() else { return }
        context.saveGState()
        context.translateBy(x: 0, y: bounds.height)
        context.scaleBy(x: 1, y: -1)
        display.textColor = .label
        display.position = CGPoint(x: origin.x, y: bounds.height - origin.y)
        display.draw(context)
        display.position = .zero  // hit-testing works from the baseline at zero
        context.restoreGState()
    }

    override func layoutSubviews() {
        super.layoutSubviews()
        hint.isHidden = !(model?.isEmpty ?? true)
        hint.sizeToFit()
        hint.frame.origin = CGPoint(x: origin.x + 10, y: origin.y - hint.frame.height + 2)
        guard let model, let display else {
            caretView.frame = CGRect(x: origin.x, y: origin.y - fontSize * 0.75, width: 2, height: fontSize)
            return
        }
        let caret = display.caretPosition(for: model.editor.caret) ?? CGPoint(x: display.width, y: 0)
        // On an empty slot the black square is the caret: no line.
        let onSlot = model.editor.mathList.atom(at: model.editor.caret)?.type == .placeholder
        caretView.isHidden = onSlot
        caretView.frame = CGRect(x: origin.x + caret.x, y: origin.y - caret.y - fontSize * 0.72, width: 2, height: fontSize * 0.95)
    }

    private var blinkTimer: Timer?

    /// Shows the caret, then blinks it with a timer. A repeating UIView animation would keep
    /// the app busy forever (UI tests wait for animations to end).
    private func blink() {
        caretView.alpha = 1
        blinkTimer?.invalidate()
        blinkTimer = Timer.scheduledTimer(withTimeInterval: 0.55, repeats: true) { [weak self] _ in
            MainActor.assumeIsolated {
                guard let caret = self?.caretView else { return }
                caret.alpha = caret.alpha > 0 ? 0 : 1
            }
        }
    }

    override func willMove(toWindow newWindow: UIWindow?) {
        super.willMove(toWindow: newWindow)
        if newWindow == nil { blinkTimer?.invalidate() }
    }

    @MainActor @objc private func tapped(_ gesture: UITapGestureRecognizer) {
        becomeFirstResponder()
        guard let display, let model else { return }
        let point = gesture.location(in: self)
        let local = CGPoint(x: point.x - origin.x, y: origin.y - point.y)
        if let index = display.closestIndex(to: local) { model.moveCaret(to: index) }
    }

    // MARK: Hardware keyboard (the on-screen keyboard is MathKeyboard, not the system one)

    override var canBecomeFirstResponder: Bool { true }
    /// No system keyboard: an empty input view.
    override var inputView: UIView? { get { UIView(frame: .zero) } set {} }
    var hasText: Bool { !(model?.isEmpty ?? true) }

    @MainActor func insertText(_ text: String) {
        guard text != "\n" else { return }
        model?.key(text)
    }

    @MainActor func deleteBackward() { model?.backspace() }

    override var keyCommands: [UIKeyCommand]? {
        [UIKeyCommand(input: UIKeyCommand.inputLeftArrow, modifierFlags: [], action: #selector(arrowLeft)),
         UIKeyCommand(input: UIKeyCommand.inputRightArrow, modifierFlags: [], action: #selector(arrowRight))]
    }

    @MainActor @objc private func arrowLeft() { model?.left() }
    @MainActor @objc private func arrowRight() { model?.right() }
}

/// The formula in SwiftUI. At least `minWidth` wide, so the whole area takes taps; wider
/// formulas scroll sideways in the ScrollView around it.
struct FormulaCanvasView: UIViewRepresentable {
    let model: FormulaEditorModel
    var minWidth: CGFloat = 0
    var height: CGFloat = 150

    func makeUIView(context: Context) -> FormulaCanvas {
        let view = FormulaCanvas()
        view.model = model
        view.refresh()
        return view
    }

    func updateUIView(_ view: FormulaCanvas, context: Context) {
        _ = model.version  // observe changes
        view.model = model
        view.refresh()
    }

    func sizeThatFits(_ proposal: ProposedViewSize, uiView: FormulaCanvas, context: Context) -> CGSize? {
        let size = uiView.intrinsicContentSize
        return CGSize(width: max(size.width, minWidth), height: max(size.height, height))
    }
}
