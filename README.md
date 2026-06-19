# Sports Widget — F1 + UFC for iOS & macOS

Two pieces:

- `sports-widget-data/` — Python scrapers + GitHub Action that rebuild a unified `feed.json` hourly. Served via GitHub Pages.
- `sports-widget-scriptable/widget.js` — single Scriptable script that renders the widget on iPhone and Mac.

Constraints satisfied: **$0**, **no Apple Developer account**, **no cable / no 7-day re-sign**, built and deployed entirely from **Windows**, real-time data, native Apple aesthetics (system fonts, squircles, Dark Mode, Mac vibrancy).

---

## 1. Deploy the data feed

### a. Create the GitHub repo
1. Create a public repo named `sports-widget-data` on GitHub.
2. From `sports-widget-data/` push the contents to it:
   ```
   git init
   git add .
   git commit -m "initial"
   git branch -M main
   git remote add origin https://github.com/<you>/sports-widget-data.git
   git push -u origin main
   ```

### b. Enable GitHub Pages
- Repo → **Settings → Pages**
- Source: **Deploy from a branch**
- Branch: `main`, Folder: `/docs`
- Save. After ~1 minute the feed will be live at:
  `https://<you>.github.io/sports-widget-data/feed.json`

### c. Confirm the cron is running
- Repo → **Actions** tab. The "Refresh feed" workflow runs hourly and on every push to `scrapers/`. It commits a new `docs/feed.json` whenever the source data changes.
- You can trigger it manually anytime via the "Run workflow" button.

### Run locally on Windows
```
py -m pip install tzdata
py scrapers/build.py
```
Writes `docs/feed.json`. Inspect it before pushing.

---

## 2. Install the widget

### iPhone
1. App Store → install **Scriptable** (free, by Simon Støvring).
2. Open `sports-widget-scriptable/widget.js`, change `FEED_URL` at the top to your Pages URL, save.
3. On the iPhone, upload `widget.js` to **iCloud Drive → Scriptable** (use [iCloud.com](https://icloud.com) in any browser on Windows). It appears in the Scriptable app instantly. Rename it to `SportsWidget` inside the app if you want a friendlier name.
4. Home screen → long-press → **Add Widget → Scriptable** → pick a size (Small / Medium / Large).
5. Long-press the placed widget → **Edit Widget** → set:
   - **Script** = `SportsWidget`
   - **Parameter** = `f1`, `ufc`, or leave blank for **auto** (shows whichever event is sooner).
6. Add a **second** widget with the other sport's parameter, then put both in a **Smart Stack** so you can swipe between F1 and UFC natively.
7. Tap any widget to open the in-app **detail view** — full session list (F1) or full main card (UFC).

### Mac (Sonoma 14+)
1. Mac App Store → install **Scriptable** (free).
2. The same `widget.js` from iCloud Drive syncs automatically.
3. Right-click desktop → **Edit Widgets** → search **Scriptable** → drag onto the desktop (or into Notification Center).
4. Configure Script + Parameter same as iPhone.
5. The widget background is left transparent on Mac so the system applies its automatic vibrancy/glass tint based on your wallpaper.

---

## 3. Architecture notes

### Data schema (`feed.json`)
```jsonc
{
  "generated_at_utc": "...",
  "generated_at_ist": "...",
  "f1":  { "next": { /* GP + sessions[] with start_utc + start_ist */ }, "upcoming": [...] },
  "ufc": { "next": { /* event + main_card[] */ }, "upcoming": [...] }
}
```
All timestamps are present in **both** UTC and pre-converted IST so the widget never does timezone math.

### Sport switching
- **Two widget instances** with `widgetParameter = f1` / `ufc` in a Smart Stack — swipe to switch. This is the Apple-native pattern; no fake interactivity hacks.
- Or use `auto` to always show whichever event is sooner.

### Expansion (tap to see all sessions / fights)
The widget's `widgetURL` deep-links into Scriptable with `?action=detail&sport=f1|ufc`, and the script presents a `UITable` with the full session/main-card list. Same UX as first-party widgets that open their host app.

### Refresh
- Server: GitHub Action cron hourly.
- Client: `widget.refreshAfterDate` hints WidgetKit to refresh every 30 min; OS may delay slightly per its scheduler.

### Forward-compat to native SwiftUI/WidgetKit
The data layer (Part A) is the durable contract. If/when you switch to Mac and want to ship a native widget, point a SwiftUI `TimelineProvider` at the same `feed.json` URL — Codable structs map 1:1. Only the renderer is rewritten.

---

## 4. Data sources

- **F1**: [OpenF1](https://openf1.org) — free, no key, session-level UTC timing.
- **UFC**: [TheSportsDB](https://www.thesportsdb.com) (`eventsnextleague` + season fallback) for the event list, plus a regex scrape of `ufc.com/event/<slug>` to pull the main-card lineup. Weight class is shown as `TBD` when UFC hasn't published it yet (typical for fights more than ~6 weeks out).

If TheSportsDB or ufc.com markup changes, the scrapers degrade gracefully — the widget renders whatever fields are present.
