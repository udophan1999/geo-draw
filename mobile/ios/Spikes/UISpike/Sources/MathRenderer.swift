import SwiftMath
import UIKit

/// A typeset formula as an image, with the baseline measurements needed to sit it in a line
/// of text: `ascent` above the baseline, `descent` below it.
struct RenderedMath {
    let image: UIImage
    let ascent: CGFloat
    let descent: CGFloat
}

@MainActor
enum MathRenderer {
    private static var cache: [String: RenderedMath] = [:]

    /// TeX Gyre Termes: Times-like (as in Vietnamese textbooks) and has every Vietnamese letter.
    static func font(size: CGFloat) -> MTFont? {
        MTFontManager().termesFont(withSize: size)
    }

    /// nil when SwiftMath cannot parse the formula; callers then show the LaTeX source.
    static func render(_ latex: String, fontSize: CGFloat, color: UIColor,
                       display: Bool = false) -> RenderedMath? {
        let key = "\(display ? "D" : "T")|\(fontSize)|\(color.description)|\(latex)"
        if let cached = cache[key] { return cached }
        var error: NSError?
        guard let list = MTMathListBuilder.build(fromString: latex, error: &error), error == nil,
              let font = font(size: fontSize),
              let line = MTTypesetter.createLineForMathList(list, font: font,
                                                             style: display ? .display : .text)
        else { return nil }
        line.textColor = color
        let size = CGSize(width: ceil(line.width) + 1, height: ceil(line.ascent + line.descent) + 1)
        let format = UIGraphicsImageRendererFormat.preferred()
        let image = UIGraphicsImageRenderer(size: size, format: format).image { context in
            let cg = context.cgContext
            cg.saveGState()
            // SwiftMath draws with y going up from the baseline.
            cg.translateBy(x: 0, y: size.height)
            cg.scaleBy(x: 1, y: -1)
            line.position = CGPoint(x: 0, y: line.descent)
            line.draw(cg)
            cg.restoreGState()
        }
        let rendered = RenderedMath(image: image, ascent: line.ascent, descent: line.descent)
        cache[key] = rendered
        return rendered
    }
}
