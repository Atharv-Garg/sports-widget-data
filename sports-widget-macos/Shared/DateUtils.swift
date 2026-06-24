import Foundation

// Helpers for parsing the feed's ISO-8601 strings and formatting them the way
// the iPhone widget does (e.g. "Sat 27 Jun · 7:30 PM IST"). The feed already
// pre-computes IST strings (*_ist), so we mostly just parse + reformat.

enum DateUtils {
    private static let iso: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime]
        return f
    }()

    private static let isoFractional: ISO8601DateFormatter = {
        let f = ISO8601DateFormatter()
        f.formatOptions = [.withInternetDateTime, .withFractionalSeconds]
        return f
    }()

    static func parse(_ s: String?) -> Date? {
        guard let s, !s.isEmpty else { return nil }
        return iso.date(from: s) ?? isoFractional.date(from: s)
    }

    // "Sat 27 Jun · 7:30 PM" rendered in IST from an *_ist string.
    static func sessionLabel(_ ist: String?) -> String {
        guard let d = parse(ist) else { return "" }
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US")
        f.timeZone = TimeZone(identifier: "Asia/Kolkata")
        f.dateFormat = "EEE d MMM · h:mm a"
        return f.string(from: d)
    }

    // "7:30 PM" only.
    static func timeOnly(_ ist: String?) -> String {
        guard let d = parse(ist) else { return "" }
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US")
        f.timeZone = TimeZone(identifier: "Asia/Kolkata")
        f.dateFormat = "EEE h:mm a"
        return f.string(from: d)
    }

    // "27 Jun" short day from any ISO string.
    static func shortDay(_ iso: String?) -> String {
        guard let d = parse(iso) else { return "" }
        let f = DateFormatter()
        f.locale = Locale(identifier: "en_US")
        f.timeZone = TimeZone(identifier: "Asia/Kolkata")
        f.dateFormat = "d MMM"
        return f.string(from: d)
    }

    // "3d 4h" countdown from now until the given UTC start. nil if past/invalid.
    static func countdown(toUtc utc: String?) -> String? {
        guard let target = parse(utc) else { return nil }
        let secs = target.timeIntervalSinceNow
        if secs <= 0 { return nil }
        let days = Int(secs) / 86_400
        let hours = (Int(secs) % 86_400) / 3_600
        if days > 0 { return "\(days)d \(hours)h" }
        let mins = (Int(secs) % 3_600) / 60
        return "\(hours)h \(mins)m"
    }
}

// Surname helper — mirrors lastName() in SportsWidget.js (strip Jr./Sr./II etc.).
extension String {
    var surnameOnly: String {
        let suffixes: Set<String> = ["jr", "jr.", "sr", "sr.", "ii", "iii", "iv"]
        let parts = split(separator: " ").map(String.init)
        guard parts.count > 1 else { return self }
        if let last = parts.last, suffixes.contains(last.lowercased()), parts.count > 2 {
            return parts[parts.count - 2]
        }
        return parts.last ?? self
    }
}
