import Foundation

// Fetches the public feed. On every success it writes a last-known-good copy to
// the Caches directory; if a later fetch fails (offline), callers fall back to
// that cache instead of bundled placeholder data.
enum FeedLoader {
    static let feedURL = "https://atharv-garg.github.io/sports-widget-data/feed.json"

    private static var cacheDir: URL {
        let base = (try? FileManager.default.url(for: .cachesDirectory, in: .userDomainMask,
                                                 appropriateFor: nil, create: true))
            ?? FileManager.default.temporaryDirectory
        let dir = base.appendingPathComponent("SportsWidget", isDirectory: true)
        try? FileManager.default.createDirectory(at: dir, withIntermediateDirectories: true)
        return dir
    }
    private static var feedCacheURL: URL { cacheDir.appendingPathComponent("feed.json") }

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
        let feed = try dec.decode(Feed.self, from: data)
        try? data.write(to: feedCacheURL)   // last-known-good, overwrites previous
        return feed
    }

    // Last successfully fetched feed, if any (used when offline).
    static func cached() -> Feed? {
        guard let data = try? Data(contentsOf: feedCacheURL) else { return nil }
        let dec = JSONDecoder()
        dec.keyDecodingStrategy = .convertFromSnakeCase
        return try? dec.decode(Feed.self, from: data)
    }

    // Bundled sample — only used on the very first run before anything is cached.
    static func sample() -> Feed {
        let dec = JSONDecoder()
        dec.keyDecodingStrategy = .convertFromSnakeCase
        let data = Data(SampleFeed.json.utf8)
        return (try? dec.decode(Feed.self, from: data)) ?? Feed(f1: nil, ufc: nil)
    }
}

// On-disk cache for fighter photos. One file per image URL; prune() keeps only
// the current card's images so it never grows past ~1.4 MB.
enum ImageStore {
    private static var dir: URL {
        let base = (try? FileManager.default.url(for: .cachesDirectory, in: .userDomainMask,
                                                 appropriateFor: nil, create: true))
            ?? FileManager.default.temporaryDirectory
        let d = base.appendingPathComponent("SportsWidgetImages", isDirectory: true)
        try? FileManager.default.createDirectory(at: d, withIntermediateDirectories: true)
        return d
    }
    private static func key(_ url: String) -> String {
        var h: UInt64 = 5381
        for b in url.utf8 { h = (h &* 33) &+ UInt64(b) }   // stable djb2
        return String(h, radix: 16) + ".img"
    }
    static func write(_ url: String, _ data: Data) { try? data.write(to: dir.appendingPathComponent(key(url))) }
    static func read(_ url: String) -> Data? { try? Data(contentsOf: dir.appendingPathComponent(key(url))) }
    static func prune(keeping urls: [String]) {
        let keep = Set(urls.map(key))
        let files = (try? FileManager.default.contentsOfDirectory(at: dir, includingPropertiesForKeys: nil)) ?? []
        for f in files where !keep.contains(f.lastPathComponent) {
            try? FileManager.default.removeItem(at: f)
        }
    }
}
