# Quickstart — Sports Widget

Everything that can be automated is done. Three manual steps remain (≈ 5 minutes total).

> Pre-baked username: `Atharv-Garg`. If your GitHub username is different, change one line in `sports-widget-data/docs/SportsWidget.js` (the `FEED_URL` constant) before step 1 and update the URL in step 1 below.

---

## Step 1 — Create the GitHub repo and push (Windows, 2 minutes)

1. Open **https://github.com/new** in any browser.
2. Repository name: **`sports-widget-data`**. Visibility: **Public** (required for free Pages). Leave everything else unchecked — do not initialize with README/.gitignore.
3. Click **Create repository**.
4. In PowerShell, push the already-prepared local repo:
   ```powershell
   cd C:\Users\atharv.garg\Documents\Projects\Widget\sports-widget-data
   git push -u origin main
   ```
   You'll be prompted for GitHub credentials the first time (use a Personal Access Token or browser auth).

---

## Step 2 — Enable GitHub Pages (browser, 30 seconds)

1. In the new repo: **Settings → Pages**.
2. **Build and deployment → Source**: **Deploy from a branch**.
3. Branch: **`main`**, folder: **`/docs`**. Click **Save**.
4. Within ~60 seconds, these two URLs go live (open them to confirm):
   - `https://atharv-garg.github.io/sports-widget-data/feed.json` — live JSON feed
   - `https://atharv-garg.github.io/sports-widget-data/SportsWidget.js` — the widget script

The hourly **Refresh feed** Action also starts running automatically — you can watch it in the repo's **Actions** tab.

---

## Step 3 — Install Scriptable + add the widget

### iPhone (≈ 90 seconds)
1. App Store → install **Scriptable** (free, by Simon Støvring).
2. In Safari on the iPhone, open:
   `https://atharv-garg.github.io/sports-widget-data/SportsWidget.js`
3. Tap the **Share** icon → **Copy**.
4. Open **Scriptable** → tap **+** (top right) → paste → tap the script name at the top → rename to **`SportsWidget`** → tap **Done**.
5. Home screen → long-press → **Add Widget** → **Scriptable** → pick a size (Small / Medium / Large) → **Add Widget**.
6. Long-press the placed widget → **Edit Widget**:
   - **Script** = `SportsWidget`
   - **Parameter** = `f1`, `ufc`, or leave blank for **auto** (whichever event is sooner)
7. Repeat for the other sport, then drop both widgets into a **Smart Stack** so you can swipe between F1 and UFC.
8. **Tap any widget** → full drill-down detail view opens (sessions / main card / upcoming events list — every upcoming row is tappable).

### Mac (Sonoma 14 or later, ≈ 60 seconds)
1. Mac App Store → install **Scriptable** (free).
2. In Safari on the Mac, open:
   `https://atharv-garg.github.io/sports-widget-data/SportsWidget.js`
3. Cmd-A → Cmd-C the whole script.
4. Open Scriptable → **+** → paste → rename to **`SportsWidget`** → Cmd-S.
5. Right-click desktop → **Edit Widgets** → search **Scriptable** → drag a Medium or Large widget onto the desktop.
6. Set **Script** = `SportsWidget`, **Parameter** = `f1` / `ufc` / blank.

The Mac widget background is transparent so the system's automatic vibrancy tints it to your wallpaper.

---

## Done

From now on:
- **Hourly**: the GitHub Action rebuilds `feed.json` with the latest F1 + UFC data.
- **Every ~30 min**: WidgetKit refreshes the widget tile.
- **Every tap**: the detail view force-fetches the latest JSON.
- **When an event ends**: it drops from the feed within ~30–60 min; the next event automatically takes its place.

No re-signing, no cable, no expiry. The script lives in Scriptable (an App Store app), so iOS treats it like any other app — it stays installed indefinitely.

---

## Troubleshooting

- **Widget shows "Error" or empty**: tap to open the detail view; if it errors there too, the feed isn't reachable. Open `https://atharv-garg.github.io/sports-widget-data/feed.json` in a browser. If 404, GitHub Pages isn't enabled yet (revisit Step 2).
- **Wrong GitHub username**: edit the first line under `// --- Theme helpers` in `SportsWidget.js` — change the `FEED_URL` constant, push, refresh the script in Scriptable.
- **Widget tile not updating**: WidgetKit refreshes at its own discretion. Force it by long-pressing → Edit → tap any setting → Done.
- **Force a feed rebuild now**: repo → **Actions** → **Refresh feed** → **Run workflow**.
