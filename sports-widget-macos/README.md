# Sports Widget — native macOS widget

A SwiftUI + WidgetKit widget for Mac (Notification Center / desktop) that reads the
**same `feed.json`** the iPhone Scriptable widget uses. F1 + UFC, auto-selecting the
sooner event.

- **Cost:** $0. **No paid Apple Developer Program.** A free Apple ID ("Personal Team")
  builds and signs locally.
- **Why not Scriptable on Mac?** Scriptable is not available in the Mac App Store
  (its developer never opted it into Mac), so a native widget is the only real option.
- **The 7-day expiry is iOS-only** — a Mac app you build and run locally keeps working
  indefinitely.

## What you get
- **UFC** (Extra Large): header, hero main-event with photos, full main card grid with
  flags/ranks/odds, and an upcoming-events list.
- **F1** (Extra Large): next-race hero with a live countdown + full session schedule (IST),
  plus drivers' and constructors' championship top 5 (powered by the new `f1.standings`
  block in the feed).
- Tapping the widget opens the official event page in your browser.
- Refreshes every 6 hours.

## Folder layout
```
sports-widget-macos/
  project.yml            XcodeGen spec (optional shortcut)
  App/                   Host app (one small window)
  Widget/                Widget extension (Provider, views, Info.plist)
  Shared/                Models, FeedLoader, Theme, DateUtils, SampleFeed
```

## Prerequisites
1. **Install Xcode** from the Mac App Store (free, ~7 GB). Open it once and accept the
   license / let it install components.
2. Sign in with your **Apple ID**: Xcode → Settings → Accounts → **+** → Apple ID.
   (No paid membership needed — it becomes a "Personal Team".)

---

## Build it — Option 1: XcodeGen (fastest)
```sh
brew install xcodegen
cd sports-widget-macos
xcodegen            # generates SportsWidget.xcodeproj
open SportsWidget.xcodeproj
```
Then in Xcode:
1. Select the **SportsWidget** target → **Signing & Capabilities** → set **Team** to your
   Apple ID (Personal Team). Repeat for the **SportsWidgetExtension** target.
2. Press **⌘R** to build & run the host app.

## Build it — Option 2: by hand in Xcode (no Homebrew)
1. **File → New → Project → macOS → App.** Name it `SportsWidget`, language **Swift**,
   interface **SwiftUI**. Save it inside `sports-widget-macos/` (or anywhere).
2. **File → New → Target → macOS → Widget Extension.** Name it `SportsWidgetExtension`.
   Uncheck "Include Live Activity" / "Include Configuration App Intent". When asked,
   **Activate** the scheme.
3. Delete the placeholder files Xcode created in the widget target (its sample
   `*.swift`). Keep the auto-generated `Info.plist` (it already has the WidgetKit
   extension point) — or replace it with `Widget/Info.plist` here.
4. **Drag the source files into the matching targets** (check "Copy items if needed"):
   - `App/SportsWidgetApp.swift` → **SportsWidget** app target (replace the default `App`
     + `ContentView` files).
   - Everything in `Widget/` (except `Info.plist`) → **SportsWidgetExtension** target.
   - Everything in `Shared/` → **both** targets (tick both boxes in the File Inspector's
     "Target Membership").
5. **Signing:** for both targets, Signing & Capabilities → Team = your Apple ID.
   Do **not** add App Groups / iCloud / Push — none are needed (keeps it free-tier).
6. **⌘R** to build & run.

> Tip: while iterating on layout, use the Xcode **canvas preview** (Editor → Canvas) on
> `UFCWidgetView` / `F1WidgetView`. They render with the bundled sample data.

---

## Install the widget on your desktop
1. Run the app once (**⌘R**). A small "Sports Widget" window confirms it's registered.
2. **Right-click the desktop → Edit Widgets** (or click the date/time in the menu bar to
   open Notification Center → Edit Widgets).
3. Search **"Sports"**, pick **Extra Large**, and drag it onto the desktop or Notification
   Center.
4. To keep it after you close Xcode: move the built app to **/Applications**
   (Product → Show Build Folder in Finder → drag `SportsWidget.app` to /Applications,
   then launch it once from there).

## Customising
- **Feed URL:** `Shared/FeedLoader.swift` → `feedURL`.
- **Refresh interval:** `Widget/Provider.swift` → the `byAdding: .hour, value: 6`.
- **Colours/fonts:** `Shared/Theme.swift`.
- **Layouts:** `Widget/UFCWidgetView.swift`, `Widget/F1WidgetView.swift`.

## Notes / limits
- Fighter photos are pre-downloaded in the timeline provider (WidgetKit can't load
  remote images at render time). If a photo is missing it falls back to a silhouette.
- macOS throttles widget refresh; the 6-hour cadence is a request, not a guarantee.
- The F1 standings come from the feed's `f1.standings` block — make sure the scraper
  (`scrapers/f1.py` + `scrapers/build.py`) has been deployed so the live feed includes it.
