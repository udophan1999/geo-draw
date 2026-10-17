import Foundation

/// Data the web app reads too, bundled from shared/ (project.yml): the symbol bar and the
/// formula gallery. Change them there, never here.
enum SharedData {
    struct Symbol: Decodable, Hashable { let symbol: String; let name: String }

    struct Template: Decodable, Hashable {
        let label: String
        /// `#?` is an empty slot, `#@` takes the selection (MathLive's syntax on the web).
        let latex: String
    }

    struct FormulaGroup: Decodable, Hashable, Identifiable {
        let id: String
        let name: String
        let wide: Bool?
        let items: [Template]
    }

    static let symbols: [Symbol] = load("symbols")
    static let formulaGroups: [FormulaGroup] = load("formula_templates")

    private static func load<T: Decodable>(_ name: String) -> [T] {
        guard let url = Bundle.main.url(forResource: name, withExtension: "json"),
              let data = try? Data(contentsOf: url),
              let value = try? JSONDecoder().decode([T].self, from: data) else {
            assertionFailure("shared/\(name).json is missing from the app bundle")
            return []
        }
        return value
    }
}
