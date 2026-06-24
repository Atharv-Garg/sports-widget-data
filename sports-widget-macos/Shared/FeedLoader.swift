import Foundation

// Fetches the same public feed the iPhone widget uses. Mirrors the JS:
// a per-minute cache-buster (?t=<unixMinute>) defeats GitHub Pages / CDN caching,
// and a 10s timeout keeps the timeline refresh snappy.

enum FeedLoader {
    static let feedURL = "https://atharv-garg.github.io/sports-widget-data/feed.json"

    static func load() async throws -> Feed {
        let minute = Int(Date().timeIntervalSince1970 / 60)
        var comps = URLComponents(string: feedURL)!
        comps.queryItems = [URLQueryItem(name: "t", value: String(minute))]

        var req = URLRequest(url: comps.url!)
        req.timeoutInterval = 10
        req.cachePolicy = .reloadIgnoringLocalAndRemoteCacheData

        let (data, _) = try await URLSession.shared.data(for: req)
        let dec = JSONDecoder()
        dec.keyDecodingStrategy = .convertFromSnakeCase
        return try dec.decode(Feed.self, from: data)
    }

    // Bundled sample for previews, the widget gallery, and offline fallback.
    static func sample() -> Feed {
        let dec = JSONDecoder()
        dec.keyDecodingStrategy = .convertFromSnakeCase
        let data = Data(SampleFeed.json.utf8)
        return (try? dec.decode(Feed.self, from: data)) ?? Feed(f1: nil, ufc: nil)
    }
}
