import Foundation
import Testing
@testable import MathMate

/// shared/fixtures/math_cases.json: the same cases web/e2e/shared-fixtures.spec.ts runs.
struct SharedFixtures: Decodable {
    struct Case: Decodable { let input: String; let expected: String }
    let normalizeMath: [Case]

    static func load() throws -> SharedFixtures {
        let bundle = Bundle(for: FixtureToken.self)
        let url = try #require(bundle.url(forResource: "math_cases", withExtension: "json"))
        return try JSONDecoder().decode(SharedFixtures.self, from: Data(contentsOf: url))
    }
}

private final class FixtureToken {}

struct MathNormalizerTests {
    @Test func matchesTheWebOnEverySharedCase() throws {
        let cases = try SharedFixtures.load().normalizeMath
        #expect(!cases.isEmpty)
        for item in cases {
            #expect(MathNormalizer.normalize(item.input) == item.expected, "\(item.input)")
        }
    }
}
