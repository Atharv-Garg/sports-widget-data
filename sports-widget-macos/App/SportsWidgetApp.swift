import SwiftUI

// Minimal host app. A widget extension must ship inside an app; this window just
// confirms the widget is installed and points the user to the widget gallery.
@main
struct SportsWidgetApp: App {
    var body: some Scene {
        WindowGroup {
            ContentView()
        }
        .windowResizability(.contentSize)
    }
}

struct ContentView: View {
    var body: some View {
        VStack(spacing: 12) {
            Image(systemName: "sportscourt")
                .font(.system(size: 40))
                .foregroundStyle(.tint)
            Text("Sports Widget")
                .font(.title2).fontWeight(.semibold)
            Text("The widget is now available.\nRight-click the desktop → Edit Widgets → drag “Sports — F1 & UFC” (Extra Large) out.")
                .multilineTextAlignment(.center)
                .foregroundStyle(.secondary)
                .font(.callout)
            Link("View live feed", destination: URL(string: FeedLoader.feedURL)!)
                .font(.callout)
        }
        .padding(40)
        .frame(width: 420)
    }
}
