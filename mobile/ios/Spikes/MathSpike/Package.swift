// swift-tools-version: 6.0
// Phase 1 spike: how much of the LaTeX MathMate uses can SwiftMath typeset?
// Run from this folder: swift run MathSpike <formulas.json> <output folder>
import PackageDescription

let package = Package(
    name: "MathSpike",
    platforms: [.macOS(.v14)],
    dependencies: [
        // Fork with arcs and \backsim (see docs/mobile-ios-spike.md).
        .package(url: "https://github.com/xuanthinhJB/SwiftMath.git", branch: "mathmate"),
    ],
    targets: [
        .executableTarget(name: "MathSpike", dependencies: ["SwiftMath"]),
    ]
)
