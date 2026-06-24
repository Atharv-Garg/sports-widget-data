import SwiftUI
import WidgetKit

// UFC layout — "Option B": header, hero main-event banner, 2-column main card
// grid with flags/ranks/odds on every fight, then an upcoming-events list.

struct UFCWidgetView: View {
    let entry: SportsEntry
    let family: WidgetFamily

    private var ev: UFCEvent? { entry.feed.ufc?.next }
    private var card: [Fight] { ev?.mainCard ?? [] }
    private var upcoming: [UFCEvent] { entry.feed.ufc?.upcoming ?? [] }

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            header
            if let main = card.first {
                hero(main)
            }
            if card.count > 1 {
                SectionLabel("Main card")
                mainCardGrid
            }
            if !upcoming.isEmpty && family == .systemExtraLarge {
                SectionLabel("Upcoming events")
                upcomingList
            }
            Spacer(minLength: 0)
        }
    }

    private var header: some View {
        HStack {
            Text("UFC · \(ev?.kind?.uppercased() ?? "EVENT")")
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(Theme.accentUFC)
            Spacer()
            Text([DateUtils.sessionLabel(ev?.mainCardStartIst), ev?.city]
                .compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: " · "))
                .font(.system(size: 11))
                .foregroundStyle(Theme.textSecondary)
                .lineLimit(1)
        }
    }

    private func hero(_ f: Fight) -> some View {
        HStack(spacing: 18) {
            fighterColumn(name: f.red, rank: f.redRank, country: f.redCountry,
                          odds: f.redOdds, img: f.redImg, corner: Theme.cornerRed)
            VStack(spacing: 2) {
                Text("VS").font(.system(size: 16, weight: .semibold))
                    .foregroundStyle(Theme.accentUFC)
                Text(weightShort(f.weightClass) + (f.titleFight == true ? " · ★" : ""))
                    .font(.system(size: 11)).foregroundStyle(Theme.textSecondary)
            }
            fighterColumn(name: f.blue, rank: f.blueRank, country: f.blueCountry,
                          odds: f.blueOdds, img: f.blueImg, corner: Theme.cornerBlue)
        }
        .frame(maxWidth: .infinity)
        .padding(8)
        .background(Theme.surfaceDeep)
        .clipShape(RoundedRectangle(cornerRadius: 12))
    }

    private func fighterColumn(name: String?, rank: String?, country: String?,
                               odds: String?, img: String?, corner: Color) -> some View {
        VStack(spacing: 2) {
            Text([flag(country), rank].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: " "))
                .font(.system(size: 11)).foregroundStyle(Theme.textSecondary)
            FighterPhoto(image: entry.image(img), corner: corner, height: 72)
            Text(name?.surnameOnly ?? "")
                .font(.system(size: 13, weight: .semibold))
                .foregroundStyle(Theme.textPrimary)
            if let odds, !odds.isEmpty, odds != "-" {
                Text(odds).font(.system(size: 11)).foregroundStyle(Theme.textSecondary)
            }
        }
    }

    private var mainCardGrid: some View {
        let rest = Array(card.dropFirst())
        let columns = [GridItem(.flexible(), spacing: 8), GridItem(.flexible(), spacing: 8)]
        return LazyVGrid(columns: columns, alignment: .leading, spacing: 8) {
            ForEach(rest) { f in mainCardCell(f) }
        }
    }

    private func mainCardCell(_ f: Fight) -> some View {
        VStack(alignment: .leading, spacing: 3) {
            Text(weightShort(f.weightClass) + (f.titleFight == true ? " · ★ Title" : ""))
                .font(.system(size: 9)).foregroundStyle(Theme.textSecondary)
                .padding(.horizontal, 5).padding(.vertical, 1)
                .background(Theme.surface).clipShape(RoundedRectangle(cornerRadius: 5))
            fightLine(name: f.red, rank: f.redRank, country: f.redCountry, odds: f.redOdds,
                      img: f.redImg, corner: Theme.cornerRed)
            fightLine(name: f.blue, rank: f.blueRank, country: f.blueCountry, odds: f.blueOdds,
                      img: f.blueImg, corner: Theme.cornerBlue)
        }
        .padding(7)
        .frame(maxWidth: .infinity, alignment: .leading)
        .background(Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: 9))
    }

    private func fightLine(name: String?, rank: String?, country: String?, odds: String?,
                           img: String?, corner: Color) -> some View {
        HStack(spacing: 6) {
            FighterPhoto(image: entry.image(img), corner: corner, height: 28, width: 24)
            Text(flag(country)).font(.system(size: 12))
            if let rank, !rank.isEmpty {
                Text(rank).font(.system(size: 11)).foregroundStyle(Theme.textSecondary)
            }
            Text(name?.surnameOnly ?? "").font(.system(size: 12, weight: .medium))
                .foregroundStyle(Theme.textPrimary).lineLimit(1)
            Spacer(minLength: 4)
            if let odds, !odds.isEmpty, odds != "-" {
                Text(odds).font(.system(size: 11)).foregroundStyle(Theme.textSecondary)
            }
        }
    }

    private var upcomingList: some View {
        VStack(spacing: 0) {
            ForEach(Array(upcoming.enumerated()), id: \.offset) { _, e in
                HStack(spacing: 8) {
                    Text(DateUtils.shortDay(e.mainCardStartUtc))
                        .font(.system(size: 11)).foregroundStyle(Theme.textSecondary)
                        .padding(.horizontal, 6).padding(.vertical, 1)
                        .background(Theme.surface).clipShape(RoundedRectangle(cornerRadius: 5))
                        .frame(width: 64, alignment: .leading)
                    Text(e.name ?? "").font(.system(size: 12)).foregroundStyle(Theme.textPrimary)
                        .lineLimit(1)
                    Spacer(minLength: 4)
                    if let city = e.city, !city.isEmpty {
                        Text(city).font(.system(size: 11)).foregroundStyle(Theme.textSecondary)
                            .lineLimit(1)
                    }
                }
                .padding(.vertical, 3)
                Divider().background(Theme.divider)
            }
        }
    }

    // "Lightweight Bout" -> "Lightweight"; "Heavyweight Title Bout" -> "Heavyweight".
    private func weightShort(_ s: String?) -> String {
        (s ?? "").replacingOccurrences(of: " Title Bout", with: "")
                 .replacingOccurrences(of: " Bout", with: "")
    }
}

// Renders a fighter cutout photo if pre-fetched, else a placeholder silhouette.
struct FighterPhoto: View {
    let image: Image?
    let corner: Color
    var height: CGFloat = 72
    var width: CGFloat? = nil

    var body: some View {
        ZStack {
            if let image {
                image.resizable().aspectRatio(contentMode: .fill)
            } else {
                Image(systemName: "person.fill")
                    .font(.system(size: height * 0.55))
                    .foregroundStyle(Theme.textTertiary)
            }
        }
        .frame(width: width ?? height * 0.85, height: height)
        .background(Theme.surface)
        .clipShape(RoundedRectangle(cornerRadius: 8))
        .overlay(alignment: .bottom) { corner.frame(height: 3) }
        .clipShape(RoundedRectangle(cornerRadius: 8))
    }
}

struct SectionLabel: View {
    let text: String
    init(_ text: String) { self.text = text }
    var body: some View {
        Text(text.uppercased())
            .font(.system(size: 10, weight: .medium))
            .tracking(0.8)
            .foregroundStyle(Theme.textSecondary)
    }
}

// Country name -> flag emoji. Covers the common UFC nationalities; falls back to "".
func flag(_ country: String?) -> String {
    guard let c = country?.trimmingCharacters(in: .whitespaces), !c.isEmpty else { return "" }
    let map: [String: String] = [
        "United States": "🇺🇸", "USA": "🇺🇸", "Brazil": "🇧🇷", "Russia": "🇷🇺",
        "Mexico": "🇲🇽", "Azerbaijan": "🇦🇿", "United Kingdom": "🇬🇧", "England": "🇬🇧",
        "Ireland": "🇮🇪", "France": "🇫🇷", "Armenia": "🇦🇲", "New Zealand": "🇳🇿",
        "Algeria": "🇩🇿", "Canada": "🇨🇦", "Australia": "🇦🇺", "Poland": "🇵🇱",
        "Georgia": "🇬🇪", "Dagestan": "🇷🇺", "China": "🇨🇳", "South Korea": "🇰🇷",
        "Spain": "🇪🇸", "Germany": "🇩🇪", "Nigeria": "🇳🇬", "Cameroon": "🇨🇲",
        "Netherlands": "🇳🇱", "Sweden": "🇸🇪", "Cuba": "🇨🇺", "Ecuador": "🇪🇨",
        "Kazakhstan": "🇰🇿", "Kyrgyzstan": "🇰🇬", "Japan": "🇯🇵", "Chile": "🇨🇱",
        "Peru": "🇵🇪", "Argentina": "🇦🇷", "Italy": "🇮🇹", "South Africa": "🇿🇦",
    ]
    return map[c] ?? ""
}
