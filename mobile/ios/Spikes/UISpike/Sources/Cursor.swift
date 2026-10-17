import SwiftMath
import SwiftUI
import UIKit

/// A formula that shows where the caret goes when tapped (the formula editor's hit-testing).
final class CaretMathView: UIView {
    var onIndex: ((String) -> Void)?
    private var display: MTMathListDisplay?
    private var caret: CGPoint?
    private let fontSize: CGFloat = 40

    var latex = "" {
        didSet {
            let list = MTMathListBuilder.build(fromString: latex)
            display = MTTypesetter.createLineForMathList(list, font: MathRenderer.font(size: fontSize), style: .display)
            caret = nil
            setNeedsDisplay()
        }
    }

    override init(frame: CGRect) {
        super.init(frame: frame)
        backgroundColor = .clear
        isAccessibilityElement = true
        accessibilityIdentifier = "formula"
        addGestureRecognizer(UITapGestureRecognizer(target: self, action: #selector(tapped)))
    }

    required init?(coder: NSCoder) { fatalError("not used") }

    /// The baseline sits here, in view coordinates (y down).
    private var origin: CGPoint {
        guard let display else { return .zero }
        return CGPoint(x: (bounds.width - display.width) / 2,
                       y: (bounds.height + display.ascent - display.descent) / 2)
    }

    /// View point (y down) to display point (y up from the baseline), and back.
    private func toDisplay(_ point: CGPoint) -> CGPoint { CGPoint(x: point.x - origin.x, y: origin.y - point.y) }
    private func toView(_ point: CGPoint) -> CGPoint { CGPoint(x: point.x + origin.x, y: origin.y - point.y) }

    @objc private func tapped(_ gesture: UITapGestureRecognizer) {
        guard let display, let index = display.closestIndex(to: toDisplay(gesture.location(in: self))) else { return }
        caret = display.caretPosition(for: index).map(toView)
        onIndex?("\(index)")
        setNeedsDisplay()
    }

    override func draw(_ rect: CGRect) {
        guard let display, let context = UIGraphicsGetCurrentContext() else { return }
        context.saveGState()
        context.translateBy(x: 0, y: bounds.height)
        context.scaleBy(x: 1, y: -1)
        display.textColor = .label
        display.position = CGPoint(x: origin.x, y: bounds.height - origin.y)
        display.draw(context)
        // Hit-testing works in display coordinates (the baseline at zero): put it back.
        display.position = .zero
        context.restoreGState()
        if let caret {
            UIColor.systemBlue.setFill()
            UIRectFill(CGRect(x: caret.x - 1, y: caret.y - fontSize * 0.75, width: 2, height: fontSize * 0.95))
        }
    }
}

struct CaretMath: UIViewRepresentable {
    let latex: String
    @Binding var index: String

    func makeUIView(context: Context) -> CaretMathView {
        let view = CaretMathView()
        view.onIndex = { value in index = value }
        return view
    }

    func updateUIView(_ view: CaretMathView, context: Context) {
        if view.latex != latex { view.latex = latex }
    }
}

struct CursorScreen: View {
    static let formulas = ["x_{1,2}=\\frac{-b\\pm\\sqrt{\\Delta}}{2a}", "AB^2+AC^2=BC^2", "\\sqrt[3]{x+1}"]
    @State private var selected = 0
    @State private var index = "Chạm vào công thức"

    var body: some View {
        VStack(spacing: 16) {
            Picker("Công thức", selection: $selected) {
                ForEach(Self.formulas.indices, id: \.self) { Text("\($0 + 1)").tag($0) }
            }
            .pickerStyle(.segmented)
            CaretMath(latex: Self.formulas[selected], index: $index)
                .frame(height: 220)
                .background(.quaternary.opacity(0.4), in: .rect(cornerRadius: 16))
            Text(verbatim: index)
                .font(.callout.monospaced())
                .accessibilityIdentifier("caretIndex")
            Spacer()
        }
        .padding(16)
        .onChange(of: selected) { index = "Chạm vào công thức" }
    }
}
