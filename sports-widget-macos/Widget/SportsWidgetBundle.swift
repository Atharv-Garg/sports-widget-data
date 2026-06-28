import WidgetKit
import SwiftUI

@main
struct SportsWidgetBundle: WidgetBundle {
    var body: some Widget {
        SportsWidget()
        F1Widget()
        UFCWidget()
    }
}

struct SportsWidget: Widget {
    let kind = "SportsWidget"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: Provider()) { entry in
            SportsWidgetEntryView(entry: entry).containerBackground(Theme.background, for: .widget)
        }
        .configurationDisplayName("Sports — F1 & UFC (auto)")
        .description("Shows whichever event is sooner.")
        .supportedFamilies([.systemExtraLarge, .systemLarge])
    }
}

struct F1Widget: Widget {
    let kind = "F1Widget"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: Provider()) { entry in
            SportsWidgetEntryView(entry: entry, forcedSport: "f1").containerBackground(Theme.background, for: .widget)
        }
        .configurationDisplayName("F1 — Race & Standings")
        .description("Next Grand Prix schedule and championship standings.")
        .supportedFamilies([.systemExtraLarge, .systemLarge])
    }
}

struct UFCWidget: Widget {
    let kind = "UFCWidget"
    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: Provider()) { entry in
            SportsWidgetEntryView(entry: entry, forcedSport: "ufc").containerBackground(Theme.background, for: .widget)
        }
        .configurationDisplayName("UFC — Fight Card")
        .description("Next UFC event main card and upcoming events.")
        .supportedFamilies([.systemExtraLarge, .systemLarge])
    }
}

struct SportsWidgetEntryView: View {
    var entry: SportsEntry
    var forcedSport: String? = nil
    @Environment(\.widgetFamily) private var family
    private var sport: String { forcedSport ?? SportPicker.soonerSport(entry.feed) }
    var body: some View {
        Group {
            if sport == "f1" {
                F1WidgetView(feed: entry.feed, family: family)
                    .widgetURL(URL(string: entry.feed.f1?.next?.externalUrl ?? ""))
            } else {
                UFCWidgetView(entry: entry, family: family)
                    .widgetURL(URL(string: entry.feed.ufc?.next?.url ?? ""))
            }
        }
    }
}
