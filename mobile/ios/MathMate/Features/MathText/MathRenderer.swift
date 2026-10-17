import SwiftMath
import UIKit

/// A typeset formula as an image, with the baseline measurements needed to sit it in a line
/// of text: `ascent` above the baseline, `descent` below it.
struct RenderedMath {
    let image: UIImage
    let ascent: CGFloat
    let descent: CGFloat
}

/// Typesets LaTeX with the SwiftMath fork (docs/mobile-ios-spike.md) into cached images.
@MainActor
enum MathRenderer {
    private static let cache = NSCache<NSString, Box>()
    private final class Box { let value: RenderedMath?; init(_ value: RenderedMath?) { self.value = value } }

    /// TeX Gyre Termes is Times-like (as in Vietnamese textbooks) and has every Vietnamese
    /// letter; formulas are drawn a little larger than the body text, whose x-height is taller.
    static let scale: CGFloat = 1.08

    static func font(size: CGFloat) -> MTFont? {
        MTFontManager().termesFont(withSize: size)
    }

    /// Commands SwiftMath does not know, written in ones it does.
    static func prepare(_ latex: String) -> String {
        latex.replacingOccurrences(of: #"\\operatorname\{([^{}]*)\}"#, with: #"\\mathrm{$1}"#,
                                   options: .regularExpression)
    }

    /// nil when SwiftMath cannot parse the formula; callers then show the LaTeX source.
    static func render(_ latex: String, fontSize: CGFloat, color: UIColor, display: Bool = false) -> RenderedMath? {
        let resolved = color.resolvedColor(with: .current)
        let key = "\(display ? "D" : "T")|\(fontSize)|\(resolved.description)|\(latex)" as NSString
        if let cached = cache.object(forKey: key) { return cached.value }
        let rendered = typeset(prepare(latex), fontSize: fontSize, color: resolved, display: display)
        cache.setObject(Box(rendered), forKey: key)
        return rendered
    }

    private static func typeset(_ latex: String, fontSize: CGFloat, color: UIColor, display: Bool) -> RenderedMath? {
        var error: NSError?
        guard let list = MTMathListBuilder.build(fromString: latex, error: &error), error == nil,
              let font = font(size: fontSize),
              let line = MTTypesetter.createLineForMathList(list, font: font, style: display ? .display : .text),
              line.width > 0
        else { return nil }
        line.textColor = color
        let size = CGSize(width: ceil(line.width) + 1, height: ceil(line.ascent + line.descent) + 1)
        let image = UIGraphicsImageRenderer(size: size).image { context in
            let cg = context.cgContext
            cg.translateBy(x: 0, y: size.height)  // SwiftMath draws with y going up
            cg.scaleBy(x: 1, y: -1)
            line.position = CGPoint(x: 0, y: line.descent)
            line.draw(cg)
        }
        return RenderedMath(image: image, ascent: line.ascent, descent: line.descent)
    }
}
