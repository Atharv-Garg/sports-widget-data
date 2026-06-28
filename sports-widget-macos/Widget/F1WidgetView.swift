import SwiftUI
import WidgetKit

struct F1WidgetView: View {
    let feed: Feed
    let family: WidgetFamily

    private var ev: F1Event? { feed.f1?.next }
    private var drivers: [DriverStanding] { feed.f1?.standings?.drivers ?? [] }
    private var constructors: [ConstructorStanding] { feed.f1?.standings?.constructors ?? [] }

    var body: some View {
        HStack(alignment: .top, spacing: 16) {
            heroColumn.frame(width: 300, alignment: .leading)
            if family == .systemExtraLarge {
                Divider().background(Theme.divider)
                driversColumn.frame(maxWidth: .infinity, alignment: .leading)
                Divider().background(Theme.divider)
                constructorsColumn.frame(maxWidth: .infinity, alignment: .leading)
            } else if !drivers.isEmpty {
                Divider().background(Theme.divider)
                driversColumn.frame(maxWidth: .infinity, alignment: .leading)
            }
        }
    }

    private var heroColumn: some View {
        VStack(alignment: .leading, spacing: 4) {
            Text("F1 · NEXT RACE").font(.system(size: 13, weight: .semibold)).foregroundStyle(Theme.accentF1)
            Text("\(ev?.flagEmoji ?? "") \(ev?.shortName ?? ev?.name ?? "")")
                .font(.system(size: 18, weight: .semibold)).foregroundStyle(Theme.textPrimary).lineLimit(1)
            Text([ev?.circuit, ev?.round.map { "Round \($0)" }].compactMap { $0 }.joined(separator: " · "))
                .font(.system(size: 11)).foregroundStyle(Theme.textSecondary)
            if let cd = DateUtils.countdown(toUtc: raceStartUtc) {
                Text("Lights out in \(cd)").font(.system(size: 14, weight: .semibold))
                    .foregroundStyle(Theme.accentF1).padding(.vertical, 6)
            } else {
                Spacer().frame(height: 8)
            }
            ForEach(Array((ev?.sessions ?? []).enumerated()), id: \.offset) { _, s in
                sessionRow(s)
            }
            Spacer(minLength: 0)
        }
    }

    private func sessionRow(_ s: Session) -> some View {
        let isRace = (s.type ?? "").lowercased() == "race"
        return VStack(spacing: 0) {
            Divider().background(Theme.divider)
            HStack {
                Text(s.type ?? "").font(.system(size: 13, weight: isRace ? .semibold : .regular))
                    .foregroundStyle(isRace ? Theme.accentF1 : Theme.textPrimary)
                Spacer()
                Text(DateUtils.timeOnly(s.startIst)).font(.system(size: 13))
                    .foregroundStyle(isRace ? Theme.accentF1 : Theme.textSecondary)
            }
            .padding(.vertical, 7)
        }
    }

    private var raceStartUtc: String? {
        ev?.sessions?.first(where: { ($0.type ?? "").lowercased() == "race" })?.startUtc ?? ev?.sessions?.last?.startUtc
    }

    private var driversColumn: some View {
        VStack(alignment: .leading, spacing: 0) {
            SectionLabel("Drivers")
            ForEach(Array(drivers.prefix(10))) { d in
                standingRow(color: d.color, pos: d.position, code: d.code, name: d.name, points: d.points)
            }
            Spacer(minLength: 0)
        }
    }

    private var constructorsColumn: some View {
        VStack(alignment: .leading, spacing: 0) {
            SectionLabel("Constructors")
            ForEach(Array(constructors.prefix(10))) { c in
                standingRow(color: c.color, pos: c.position, code: nil, name: c.name, points: c.points)
            }
            Spacer(minLength: 0)
        }
    }

    private func standingRow(color: String?, pos: Int?, code: String?, name: String?, points: Double?) -> some View {
        VStack(spacing: 0) {
            Divider().background(Theme.divider)
            HStack(spacing: 8) {
                if let code, !code.isEmpty {
                    Text(code).font(.system(size: 10, weight: .medium))
                        .foregroundStyle(Theme.textTertiary).frame(width: 30, alignment: .leading)
                }
                RoundedRectangle(cornerRadius: 2).fill(Color(hexString: color ?? "#9b9b9f")).frame(width: 3, height: 18)
                Text("\(pos ?? 0) \(name ?? "")").font(.system(size: 13)).foregroundStyle(Theme.textPrimary).lineLimit(1)
                Spacer(minLength: 4)
                Text(pointsStr(points)).font(.system(size: 13, weight: .semibold)).foregroundStyle(Theme.textPrimary)
            }
            .padding(.vertical, 6)
        }
    }

    private func pointsStr(_ p: Double?) -> String {
        guard let p else { return "0" }
        return p.truncatingRemainder(dividingBy: 1) == 0 ? String(Int(p)) : String(p)
    }
}
