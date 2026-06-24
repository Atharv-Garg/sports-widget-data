import SwiftUI
import AppKit

// Colours ported from SportsWidget.js. Each uses an NSColor dynamic provider so
// it adapts automatically to light/dark mode, matching Color.dynamic() in the JS.

extension Color {
    init(hexString: String) {
        var s = hexString.trimmingCharacters(in: .whitespacesAndNewlines)
        if s.hasPrefix("#") { s.removeFirst() }
        var v: UInt64 = 0
        Scanner(string: s).scanHexInt64(&v)
        let r = Double((v & 0xFF0000) >> 16) / 255
        let g = Double((v & 0x00FF00) >> 8) / 255
        let b = Double(v & 0x0000FF) / 255
        self = Color(red: r, green: g, blue: b)
    }

    static func dynamic(_ light: String, _ dark: String) -> Color {
        Color(nsColor: NSColor(name: nil) { appearance in
            let isDark = appearance.bestMatch(from: [.aqua, .darkAqua]) == .darkAqua
            return NSColor(Color(hexString: isDark ? dark : light))
        })
    }
}

enum Theme {
    static let accentF1 = Color.dynamic("#E10600", "#FF5C5C")
    static let accentUFC = Color.dynamic("#D20A0A", "#FF7A1A")

    static let background = Color.dynamic("#FFFFFF", "#1C1C1E")
    static let surface = Color.dynamic("#F2F2F7", "#262628")
    static let surfaceDeep = Color.dynamic("#EAEAEF", "#161618")

    static let textPrimary = Color.dynamic("#000000", "#FFFFFF")
    static let textSecondary = Color.dynamic("#6C6C70", "#9B9B9F")
    static let textTertiary = Color.dynamic("#9B9B9F", "#7C7C80")

    static let divider = Color.dynamic("#D9D9DE", "#38383A")

    static let cornerRed = Color(hexString: "#FF5B4D")
    static let cornerBlue = Color(hexString: "#4A9BFF")
}
