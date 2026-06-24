import SwiftUI
import WidgetKit

// F1 layout — "Option A with Option-C hero": left column is the next-race hero
// (flag, GP name, circuit · round, countdown, full session list), middle is the
// drivers' championship top 5, right is the constructors' championship top 5.

struct F1WidgetView: View {
    let feed: Feed
    let family: WidgetFamily

    private var ev: F1Event? { feed.f1?.next }
    private var drivers: [DriverStanding] { feed.f1?.standings?.drivers ?? [] }
    private var constructors: [ConstructorStanding] { feed.f1?.standings?.constructors ?? [] }

    var body: some View {
        HStack(alignment: .top, spacing: 16) {
            heroColumn
                .frame(maxWidth: .infinity, alignment: .leading)
            if family == .systemExtraLarge {
                Divider().background(Theme.divider)
                driversColumn.frame(maxWidth: .infinity, alignment: .leading)
                constructorsColumn.frame(maxWidth: .infinity, alignment: .leading)
            } else if !drivers.isEmpty {
                Divider().background(Theme.divider)
                driversColumn.frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }

    private var heroColumn: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("F1 · NEXT RACE")
                .font(.system(size: 12, weight: .semibold))
                .foregroundStyle(Theme.accentF1)
            Text("\(ev?.flagEmoji ?? "") \(ev?.shortName ?? ev?.name ?? "")")
                .font(.system(size: 17, weight: .semibold))
                .foregroundStyle(Theme.textPrimary)
                .lineLimit(1)
            Text([ev?.circuit, ev?.round.map { "Round \($0)" }]
                .compactMap { $0 }.joined(separator: " · "))
                .font(.system(size: 11)).foregroundStyle(Theme.textSecondary)

            if let cd = DateUtils.countdown(toUtc: raceStartUtc) {
                Text("Lights out in \(cd)")
                    .font(.system(size: 13, weight: .semibold))
                    .foregroundStyle(Theme.accentF1)
                    .padding(.top, 4)
            }

            VStack(spacing: 0) {
                ForEach(Array((ev?.sessions ?? []).enumerated()), id: \.offset) { _, s in
                    let isRace = (s.type ?? "").lowercased() == "race"
                    HStack {
                        Text(s.type ?? "").font(.system(size: 12, weight: isRace ? .semibold : .regular))
                            .foregroundStyle(isRace ? Theme.accentF1 : Theme.textPrimary)
                        Spacer()
                        Text(DateUtils.timeOnly(s.startIst))
                            .font(.system(size: 12))
                            .foregroundStyle(isRace ? Theme.accentF1 : Theme.textSecondary)
                    }
                    .padding(.vertical, 3)
                    Divider().background(Theme.divider)
                }
            }
            .padding(.top, 4)
        }
    }

    private var raceStartUtc: String? {
        ev?.sessions?.first(where: { ($0.type ?? "").lowercased() == "race" })?.startUtc
            ?? ev?.sessions?.last?.startUtc
    }

    private var driversColumn: some View {
        VStack(alignment: .leading, spacing: 0) {
            SectionLabel("Drivers")
            ForEach(drivers) { d in
                HStack(spacing: 8) {
                    Text(d.code ?? "")
                        .font(.system(size: 9, weight: .medium))
                        .frame(width: 26, height: 24)
                        .background(Theme.surface)
                        .clipShape(Circle())
                        .foregroundStyle(Theme.textSecondary)
                    RoundedRectangle(cornerRadius: 2)
                        .fill(Color(hexString: d.color ?? "#9b9b9f"))
                        .frame(width: 3, height: 18)
                    Text("\(d.position ?? 0) \(d.name ?? "")")
                        .font(.system(size: 12)).foregroundStyle(Theme.textPrimary)
                        .lineLimit(1)
                    Spacer(minLength: 4)
                    Text(points(d.points)).font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(Theme.textPrimary)
                }
                .padding(.vertical, 4)
                Divider().background(Theme.divider)
            }
        }
    }

    private var constructorsColumn: some View {
        VStack(alignment: .leading, spacing: 0) {
            SectionLabel("Constructors")
            ForEach(constructors) { c in
                HStack(spacing: 8) {
                    RoundedRectangle(cornerRadius: 2)
                        .fill(Color(hexString: c.color ?? "#9b9b9f"))
                        .frame(width: 3, height: 18)
                    Text("\(c.position ?? 0) \(c.name ?? "")")
                        .font(.system(size: 12)).foregroundStyle(Theme.textPrimary)
                        .lineLimit(1)
                    Spacer(minLength: 4)
                    Text(points(c.points)).font(.system(size: 12, weight: .semibold))
                        .foregroundStyle(Theme.textPrimary)
                }
                .padding(.vertical, 4)
                Divider().background(Theme.divider)
            }
        }
    }

    private func points(_ p: Double?) -> String {
        guard let p else { return "0" }
        return p.truncatingRemainder(dividingBy: 1) == 0 ? String(Int(p)) : String(p)
    }
}
