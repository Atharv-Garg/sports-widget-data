import SwiftUI
import WidgetKit

struct UFCWidgetView: View {
    let entry: SportsEntry
    let family: WidgetFamily

    private var ev: UFCEvent? { entry.feed.ufc?.next }
    private var card: [Fight] { ev?.mainCard ?? [] }
    private var upcoming: [UFCEvent] { entry.feed.ufc?.upcoming ?? [] }

    // Fixed row heights → the GeometryReader auto-fit math is exact.
    private let mainRowH: CGFloat = 44
    private let upRowH: CGFloat = 30
    private let labelH: CGFloat = 18

    var body: some View {
        if family == .systemExtraLarge { extraLarge } else { large }
    }

    private var extraLarge: some View {
        GeometryReader { geo in
            HStack(alignment: .top, spacing: 16) {
                VStack(alignment: .leading, spacing: 6) {
                    header
                    Spacer(minLength: 8)
                    if let main = card.first { hero(main) }
                    Spacer(minLength: 0)
                }
                .frame(width: 250, alignment: .leading)

                Divider().background(Theme.divider)

                rightColumn(geo.size.height)
                    .frame(maxWidth: .infinity, alignment: .topLeading)
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity, alignment: .topLeading)
        }
    }

    // Renders the main card, then exactly as many upcoming events as fit.
    private func rightColumn(_ availableH: CGFloat) -> some View {
        let mainRows = max(card.count - 1, 0)
        let usedByMain = card.count > 1 ? labelH + CGFloat(mainRows) * mainRowH : 0
        let remaining = availableH - usedByMain - labelH - 2
        let fit = max(0, Int((remaining / upRowH).rounded(.down)))
        let shown = Array(upcoming.prefix(fit))
        return VStack(alignment: .leading, spacing: 0) {
            if card.count > 1 {
                SectionLabel("Main card")
                ForEach(Array(card.dropFirst())) { f in cardRow(f) }
            }
            if !shown.isEmpty {
                SectionLabel("Upcoming events").padding(.top, 8)
                ForEach(Array(shown.enumerated()), id: \.offset) { _, e in upcomingRow(e) }
            }
            Spacer(minLength: 0)
        }
    }

    private var large: some View {
        VStack(alignment: .leading, spacing: 6) {
            header
            if let main = card.first { hero(main) }
            if card.count > 1 {
                SectionLabel("Main card")
                ForEach(Array(card.dropFirst().prefix(3))) { f in cardRow(f) }
            }
            Spacer(minLength: 0)
        }
    }

    private var header: some View {
        VStack(alignment: .leading, spacing: 2) {
            Text("UFC · \(ev?.kind?.uppercased() ?? "EVENT")")
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(Theme.accentUFC)
            if let name = ev?.name, !name.isEmpty {
                Text(name)
                    .font(.system(size: 15, weight: .semibold))
                    .foregroundStyle(Theme.textPrimary).lineLimit(2)
            }
            Text([DateUtils.sessionLabel(ev?.mainCardStartIst), ev?.venue, ev?.city]
                .compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: " · "))
                .font(.system(size: 11)).foregroundStyle(Theme.textSecondary).lineLimit(2)
        }
    }

    private func hero(_ f: Fight) -> some View {
        VStack(spacing: 6) {
            HStack(alignment: .bottom, spacing: 12) {
                fighterColumn(name: f.red, rank: f.redRank, country: f.redCountry,
                              odds: f.redOdds, img: f.redImg, corner: Theme.cornerRed)
                Text("VS").font(.system(size: 17, weight: .semibold))
                    .foregroundStyle(Theme.accentUFC).padding(.bottom, 36)
                fighterColumn(name: f.blue, rank: f.blueRank, country: f.blueCountry,
                              odds: f.blueOdds, img: f.blueImg, corner: Theme.cornerBlue)
            }
            Text(weightShort(f.weightClass) + (f.titleFight == true ? " · ★ Title" : "") + " · Main event")
                .font(.system(size: 12)).foregroundStyle(Theme.textSecondary)
        }
        .frame(maxWidth: .infinity)
    }

    private func fighterColumn(name: String?, rank: String?, country: String?,
                               odds: String?, img: String?, corner: Color) -> some View {
        VStack(spacing: 3) {
            Text([flag(country), rank].compactMap { $0 }.filter { !$0.isEmpty }.joined(separator: " "))
                .font(.system(size: 12)).foregroundStyle(Theme.textSecondary)
            FighterPhoto(image: entry.image(img), corner: corner, height: 118, width: 96)
            Text(name?.surnameOnly ?? "").font(.system(size: 15, weight: .semibold)).foregroundStyle(Theme.textPrimary).lineLimit(1).minimumScaleFactor(0.6)
            if let odds, !odds.isEmpty, odds != "-" {
                Text(odds).font(.system(size: 12)).foregroundStyle(Theme.textSecondary)
            }
        }
    }

    private func cardRow(_ f: Fight) -> some View {
        VStack(spacing: 0) {
            Divider().background(Theme.divider)
            HStack(spacing: 8) {
                Text(weightAbbr(f.weightClass))
                    .font(.system(size: 9, weight: .medium)).foregroundStyle(Theme.textSecondary)
                    .frame(width: 30).padding(.vertical, 2)
                    .background(Theme.surface).clipShape(RoundedRectangle(cornerRadius: 5))
                fighterMini(name: f.red, rank: f.redRank, country: f.redCountry, odds: f.redOdds,
                            img: f.redImg, corner: Theme.cornerRed)
                Text("v").font(.system(size: 11)).foregroundStyle(Theme.textTertiary)
                fighterMini(name: f.blue, rank: f.blueRank, country: f.blueCountry, odds: f.blueOdds,
                            img: f.blueImg, corner: Theme.cornerBlue)
                if f.titleFight == true { Text("★").font(.system(size: 11)).foregroundStyle(Theme.accentUFC) }
            }
            .frame(maxHeight: .infinity)
        }
        .frame(height: mainRowH)
    }

    private func fighterMini(name: String?, rank: String?, country: String?, odds: String?,
                             img: String?, corner: Color) -> some View {
        HStack(spacing: 5) {
            FighterPhoto(image: entry.image(img), corner: corner, height: 30, width: 22)
            Text(flag(country)).font(.system(size: 11))
            if let rank, !rank.isEmpty { Text(rank).font(.system(size: 10)).foregroundStyle(Theme.textTertiary) }
            Text(name?.surnameOnly ?? "").font(.system(size: 13, weight: .medium))
                .foregroundStyle(Theme.textPrimary).lineLimit(1)
            if let odds, !odds.isEmpty, odds != "-" {
                Text(odds).font(.system(size: 11)).foregroundStyle(Theme.textSecondary)
            }
        }
        .frame(maxWidth: .infinity, alignment: .leading)
    }

    private func upcomingRow(_ e: UFCEvent) -> some View {
        VStack(spacing: 0) {
            Divider().background(Theme.divider)
            HStack(spacing: 8) {
                Text(DateUtils.shortDay(e.mainCardStartUtc))
                    .font(.system(size: 11)).foregroundStyle(Theme.textSecondary)
                    .frame(width: 52, alignment: .leading)
                Text(e.name ?? "").font(.system(size: 12)).foregroundStyle(Theme.textPrimary).lineLimit(1)
                Spacer(minLength: 4)
            }
            .frame(maxHeight: .infinity)
        }
        .frame(height: upRowH)
    }

    private func weightShort(_ s: String?) -> String {
        (s ?? "").replacingOccurrences(of: " Title Bout", with: "").replacingOccurrences(of: " Bout", with: "")
    }

    private func weightAbbr(_ s: String?) -> String {
        let w = weightShort(s).lowercased()
        let map: [String: String] = [
            "women's strawweight": "WSW", "women's flyweight": "WFL",
            "women's bantamweight": "WBW", "women's featherweight": "WFW",
            "strawweight": "SW", "flyweight": "FLY", "bantamweight": "BW",
            "featherweight": "FW", "lightweight": "LW", "welterweight": "WW",
            "middleweight": "MW", "light heavyweight": "LHW", "heavyweight": "HW",
            "catchweight": "CW",
        ]
        return map[w] ?? String(weightShort(s).prefix(3)).uppercased()
    }
}

struct FighterPhoto: View {
    let image: Image?
    let corner: Color
    var height: CGFloat = 72
    var width: CGFloat? = nil

    var body: some View {
        let w = width ?? height * 0.82
        ZStack(alignment: .top) {
            Theme.surface
            if let image {
                image.resizable().aspectRatio(contentMode: .fill)
                    .frame(width: w, height: height, alignment: .top)
            } else {
                Image(systemName: "person.fill")
                    .font(.system(size: height * 0.5))
                    .foregroundStyle(Theme.textTertiary)
                    .frame(height: height)
            }
        }
        .frame(width: w, height: height)
        .clipped()
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

func flag(_ country: String?) -> String {
    guard let c = country?.trimmingCharacters(in: .whitespaces), !c.isEmpty else { return "" }
    let map: [String: String] = [
        "United States": "🇺🇸", "USA": "🇺🇸", "Brazil": "🇧🇷", "Russia": "🇷🇺",
        "Mexico": "🇲🇽", "Azerbaijan": "🇦🇿", "United Kingdom": "🇬🇧", "England": "🇬🇧",
        "Ireland": "🇮🇪", "France": "🇫🇷", "Armenia": "🇦🇲", "New Zealand": "🇳🇿",
        "Algeria": "🇩🇿", "Canada": "🇨🇦", "Australia": "🇦🇺", "Poland": "🇵🇱",
        "Georgia": "🇬🇪", "China": "🇨🇳", "South Korea": "🇰🇷",
        "Spain": "🇪🇸", "Germany": "🇩🇪", "Nigeria": "🇳🇬", "Cameroon": "🇨🇲",
        "Netherlands": "🇳🇱", "Sweden": "🇸🇪", "Cuba": "🇨🇺", "Ecuador": "🇪🇨",
        "Kazakhstan": "🇰🇿", "Kyrgyzstan": "🇰🇬", "Japan": "🇯🇵", "Chile": "🇨🇱",
        "Peru": "🇵🇪", "Argentina": "🇦🇷", "Italy": "🇮🇹", "South Africa": "🇿🇦",
    ]
    return map[c] ?? ""
}
