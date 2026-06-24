import WidgetKit
import SwiftUI

@main
struct SportsWidgetBundle: WidgetBundle {
    var body: some Widget {
        SportsWidget()
    }
}

struct SportsWidget: Widget {
    let kind = "SportsWidget"

    var body: some WidgetConfiguration {
        StaticConfiguration(kind: kind, provider: Provider()) { entry in
            SportsWidgetEntryView(entry: entry)
                .containerBackground(Theme.background, for: .widget)
        }
        .configurationDisplayName("Sports — F1 & UFC")
        .description("Next F1 race weekend and the upcoming UFC card.")
        .supportedFamilies([.systemExtraLarge, .systemLarge])
    }
}

struct SportsWidgetEntryView: View {
    var entry: SportsEntry
    @Environment(\.widgetFamily) private var family

    private var sport: String { SportPicker.soonerSport(entry.feed) }

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
