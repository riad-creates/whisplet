import AppKit
import SwiftUI

enum AppBrand {
    static let name = "Whisplet"
}

enum AppTheme {
    static let background = Color(red: 0.975, green: 0.976, blue: 0.987)
    static let sidebar = Color(red: 0.949, green: 0.951, blue: 0.965)
    static let surface = Color.white
    static let surfaceRaised = Color(red: 0.956, green: 0.958, blue: 0.979)
    static let border = Color(red: 0.86, green: 0.875, blue: 0.91)
    static let text = Color(red: 0.12, green: 0.13, blue: 0.18)
    static let muted = Color(red: 0.40, green: 0.43, blue: 0.50)
    static let accent = Color(red: 0.31, green: 0.29, blue: 0.78)
    static let accentSoft = Color(red: 0.90, green: 0.90, blue: 0.98)
    static let warm = accent
    static let healthy = Color(red: 0.15, green: 0.48, blue: 0.36)
    static let nsBackground = NSColor(calibratedRed: 0.975, green: 0.976, blue: 0.987, alpha: 1)
}

struct WhispletMark: View {
    var body: some View {
        GeometryReader { proxy in
            let w = proxy.size.width
            let h = proxy.size.height
            Path { path in
                path.move(to: CGPoint(x: w * 0.1, y: h * 0.5))
                path.addCurve(to: CGPoint(x: w * 0.4, y: h * 0.5),
                    control1: CGPoint(x: w * 0.2, y: h * 0.05),
                    control2: CGPoint(x: w * 0.3, y: h * 0.95))
                path.addCurve(to: CGPoint(x: w * 0.7, y: h * 0.5),
                    control1: CGPoint(x: w * 0.5, y: h * 0.05),
                    control2: CGPoint(x: w * 0.6, y: h * 0.95))
            }
            .stroke(AppTheme.accent, style: StrokeStyle(lineWidth: w * 0.075, lineCap: .round))
            Capsule().fill(AppTheme.text)
                .frame(width: w * 0.07, height: h * 0.52)
                .position(x: w * 0.88, y: h * 0.5)
        }
        .accessibilityHidden(true)
    }
}
