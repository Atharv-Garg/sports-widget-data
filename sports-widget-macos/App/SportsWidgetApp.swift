import SwiftUI
import WidgetKit
import AppKit

// Hidden background agent (LSUIElement). Launches at login, refreshes all
// widgets immediately and then every 30 minutes so the Mac widget stays current
// without the user opening anything.
@main
struct SportsWidgetApp: App {
    @NSApplicationDelegateAdaptor(AppDelegate.self) private var delegate
    var body: some Scene {
        Settings { EmptyView() }
    }
}

final class AppDelegate: NSObject, NSApplicationDelegate {
    private var timer: Timer?
    func applicationDidFinishLaunching(_ notification: Notification) {
        WidgetCenter.shared.reloadAllTimelines()
        timer = Timer.scheduledTimer(withTimeInterval: 30 * 60, repeats: true) { _ in
            WidgetCenter.shared.reloadAllTimelines()
        }
        // wake from sleep -> refresh shortly after
        NSWorkspace.shared.notificationCenter.addObserver(
            forName: NSWorkspace.didWakeNotification, object: nil, queue: .main) { _ in
            WidgetCenter.shared.reloadAllTimelines()
        }
    }
}
