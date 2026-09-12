import XCTest
@testable import PhononBar

final class F5HotKeyTests: XCTestCase {
    func testHoldIgnoresRepeatsAndUnmatchedReleases() {
        var edges = HoldKeyEdges()
        XCTAssertNil(edges.receive(pressed: false))
        XCTAssertEqual(edges.receive(pressed: true), true)
        XCTAssertNil(edges.receive(pressed: true))
        XCTAssertEqual(edges.receive(pressed: false), false)
        XCTAssertNil(edges.receive(pressed: false))
        XCTAssertEqual(edges.receive(pressed: true), true)
    }

    func testF5ModesDoNotAcceptOtherHoldKeys() {
        XCTAssertEqual(ShortcutPolicy.sources(for: "f5"), ["f5"])
        XCTAssertEqual(ShortcutPolicy.sources(for: "f5_and_control_space"), ["f5", "control-space"])
        XCTAssertFalse(ShortcutPolicy.allows(mode: "both", source: "f5"))
        XCTAssertTrue(ShortcutPolicy.allows(mode: "f5", source: "menu"))
    }

    func testExplicitCleanupChoiceSurvivesDefaultChange() throws {
        let settings = try JSONDecoder().decode(NativeSettings.self,
            from: Data(#"{"schema_version":2,"ai_cleanup":true}"#.utf8))
        XCTAssertTrue(settings.aiCleanup)
        XCTAssertFalse(NativeSettings().aiCleanup)
    }
}
