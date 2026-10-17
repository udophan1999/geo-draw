import SwiftUI

// Liquid Glass on iOS 26, with a fallback for iOS 17–25. Every glass surface in the app goes
// through these, so raising the minimum iOS later changes only this file. Glass is for the
// control layer (composer, tutor bar, toolbars), never for content such as message bubbles.

extension View {
    /// A glass surface in `shape`; `interactive` makes it react to touches on iOS 26.
    @ViewBuilder
    func mmGlass<S: Shape>(in shape: S, interactive: Bool = false) -> some View {
        if #available(iOS 26, *) {
            glassEffect(interactive ? .regular.interactive() : .regular, in: shape)
        } else {
            background(.ultraThinMaterial, in: shape)
                .overlay(shape.stroke(.primary.opacity(0.08), lineWidth: 0.5))
        }
    }

    /// Lets glass shapes inside an `MMGlassContainer` morph into each other on iOS 26.
    @ViewBuilder
    func mmGlassID<ID: Hashable & Sendable>(_ id: ID, in namespace: Namespace.ID) -> some View {
        if #available(iOS 26, *) {
            glassEffectID(id, in: namespace)
        } else {
            self
        }
    }

    /// A glass button on iOS 26, a bordered one before.
    @ViewBuilder
    func mmGlassButton(prominent: Bool = false) -> some View {
        if #available(iOS 26, *) {
            if prominent { buttonStyle(.glassProminent) } else { buttonStyle(.glass) }
        } else {
            if prominent { buttonStyle(.borderedProminent) } else { buttonStyle(.bordered) }
        }
    }
}

/// Groups glass shapes so they blend and morph (GlassEffectContainer on iOS 26).
struct MMGlassContainer<Content: View>: View {
    var spacing: CGFloat?
    @ViewBuilder var content: Content

    var body: some View {
        if #available(iOS 26, *) {
            GlassEffectContainer(spacing: spacing) { content }
        } else {
            content
        }
    }
}
