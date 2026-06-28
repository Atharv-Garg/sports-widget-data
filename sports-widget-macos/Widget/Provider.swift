import WidgetKit
import SwiftUI
import AppKit

// Timeline entry carries the decoded feed plus any pre-downloaded fighter photos.
// WidgetKit views can't reliably load remote images at render time, so the
// provider fetches them up front and the views read them from `images`.
struct SportsEntry: TimelineEntry {
    let date: Date
    let feed: Feed
    let images: [String: Data]

    func image(_ url: String?) -> Image? {
        guard let url, !url.isEmpty, let data = images[url],
              let ns = NSImage(data: data) else { return nil }
        return Image(nsImage: ns)
    }
}

struct Provider: TimelineProvider {
    func placeholder(in context: Context) -> SportsEntry {
        SportsEntry(date: .now, feed: FeedLoader.sample(), images: [:])
    }

    func getSnapshot(in context: Context, completion: @escaping (SportsEntry) -> Void) {
        completion(SportsEntry(date: .now, feed: FeedLoader.sample(), images: [:]))
    }

    func getTimeline(in context: Context, completion: @escaping (Timeline<SportsEntry>) -> Void) {
        Task {
            let feed = (try? await FeedLoader.load()) ?? FeedLoader.sample()
            let images = await prefetchImages(feed)
            let entry = SportsEntry(date: .now, feed: feed, images: images)
            // Fixed 6-hour refresh — catches newly announced events same-day; negligible load.
            let next = Calendar.current.date(byAdding: .hour, value: 1, to: .now) ?? .now.addingTimeInterval(21_600)
            completion(Timeline(entries: [entry], policy: .after(next)))
        }
    }

    private func prefetchImages(_ feed: Feed) async -> [String: Data] {
        var urls: [String] = []
        for f in feed.ufc?.next?.mainCard ?? [] {
            for u in [f.redImg, f.blueImg] {
                if let u, !u.isEmpty { urls.append(u) }
            }
        }
        var out: [String: Data] = [:]
        for u in urls where out[u] == nil {
            guard let url = URL(string: u) else { continue }
            var req = URLRequest(url: url)
            req.timeoutInterval = 8
            if let (data, _) = try? await URLSession.shared.data(for: req) {
                out[u] = data
            }
        }
        return out
    }
}

// Which sport is sooner — mirrors the "auto" logic in SportsWidget.js.
enum SportPicker {
    static func soonerSport(_ feed: Feed) -> String {
        let f1Start = DateUtils.parse(feed.f1?.next?.sessions?.first?.startUtc)
        let ufcStart = DateUtils.parse(feed.ufc?.next?.mainCardStartUtc)
        switch (f1Start, ufcStart) {
        case let (.some(a), .some(b)): return a <= b ? "f1" : "ufc"
        case (.some, .none): return "f1"
        case (.none, .some): return "ufc"
        default: return "ufc"
        }
    }
}
