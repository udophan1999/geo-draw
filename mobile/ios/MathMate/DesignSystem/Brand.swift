import SwiftUI
import UIKit

/// The name shown to users. The app never names the AI provider (CLAUDE.md).
enum Brand {
    static let appName = "MathMate"
    /// The web's primary blue (web/src/index.css).
    static let primary = Color.accentColor
}

/// Light taps for the moments that matter: a deeper hint, a sent message, a finished drawing.
@MainActor
enum Haptics {
    static func selection() { UISelectionFeedbackGenerator().selectionChanged() }
    static func success() { UINotificationFeedbackGenerator().notificationOccurred(.success) }
    static func warning() { UINotificationFeedbackGenerator().notificationOccurred(.warning) }
    static func tap() { UIImpactFeedbackGenerator(style: .light).impactOccurred() }
}
