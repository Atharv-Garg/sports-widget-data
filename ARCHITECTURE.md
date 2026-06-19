# How the Sports Widget Works

A plain-language walkthrough of the complete flow. Read this if you ever forget which piece of code lives where, or why the system is split the way it is.

---

## The three computers

The system has **three different computers** that never talk to each other directly — they communicate through a single file they pass around. Once you see who does what, the rest clicks.

```
┌─────────────────────┐    ┌────────────────────┐    ┌────────────────┐
│ Your Windows PC     │    │ GitHub's servers   │    │ Your iPhone    │
│                     │    │                    │    │                │
│ - Writes code       │    │ - Runs the cron    │    │ - Renders the  │
│ - Pushes to GitHub  │    │ - Hosts the file   │    │   widget       │
│                     │    │                    │    │                │
│ Active: only when   │    │ Active: every hour │    │ Active: every  │
│ you push changes    │    │ automatically      │    │ ~30 min        │
└─────────────────────┘    └────────────────────┘    └────────────────┘
```

Each computer runs **different code in different languages**, and **they never talk to each other directly**. They pass one file around: `feed.json`.

---

## The shared file: feed.json

Think of `feed.json` as a printed schedule pinned to a public noticeboard.

- GitHub's servers update the noticeboard every hour with the latest schedule.
- Your iPhone walks past the noticeboard every 30 minutes and reads what's pinned.
- Your Windows PC writes the *rules* for what the schedule looks like (the format) and *how* GitHub builds it (the scrapers) — but doesn't itself produce the schedule.

That's the whole system. Three computers, one noticeboard.

---

## A day in the life — timeline view

Walking through what actually happens between 2 PM and 4 PM on a normal day.

### 2:00 PM — Nothing is happening

- Windows PC: off, or you're using Excel. No widget code involved.
- GitHub: idle, waiting for cron to fire.
- iPhone: showing whatever the widget rendered last time.

### 3:00 PM — GitHub's hourly cron fires (the most important moment)

GitHub spins up a temporary virtual machine in some data center. On that VM, it executes these steps in order:

```
[VM spins up, runs Ubuntu Linux for ~30 seconds total]
│
├─ Step 1: Download the latest version of your repo
│          (git clone https://github.com/Atharv-Garg/sports-widget-data)
│
├─ Step 2: Install Python 3.12 and BeautifulSoup
│          (pip install beautifulsoup4)
│
├─ Step 3: Run Python: `python scrapers/build.py`
│          │
│          ├─ build.py calls f1.py
│          │   └─ f1.py hits api.openf1.org, gets F1 calendar JSON
│          │
│          ├─ build.py calls ufc.py
│          │   └─ ufc.py hits ufc.com/events, parses with BeautifulSoup
│          │   └─ For each event, ufc.py hits ufc.com/event/<slug>
│          │   └─ If anything fails, ufc_espn.py hits ESPN as backup
│          │
│          └─ build.py merges everything, converts to IST,
│              writes to /tmp/.../docs/feed.json on the VM
│
├─ Step 4: Compare new feed.json to what was in the repo last hour.
│          If identical: do nothing. If changed: git commit + git push.
│
└─ VM is destroyed. Total elapsed time: ~30 seconds.
```

After this 30-second job, the VM no longer exists. But the new `feed.json` is now sitting in the public repo.

### 3:00:30 PM — GitHub Pages auto-republishes

GitHub notices the repo changed. Its Pages system grabs `docs/feed.json` and copies it to GitHub's static-file servers (and from there, to Cloudflare's CDN cache).

Now anyone on the internet can go to:

```
https://atharv-garg.github.io/sports-widget-data/feed.json
```

…and get the latest version. The "noticeboard" is updated.

### 3:00:30 PM to 3:25 PM — iPhone does nothing

iOS WidgetKit decides when to refresh widgets. It may be 5 minutes from the last refresh, or it may be 25 minutes. You don't control this. The widget tile keeps showing whatever it last rendered.

### 3:25 PM — iOS decides to refresh the UFC widget

iOS sends a "render this widget" request to the Scriptable app on your phone. Scriptable wakes up. It runs the JavaScript file you pasted earlier — `SportsWidget.js`. That JavaScript executes inside Scriptable's process, on your phone, using your phone's CPU and battery.

```
[Scriptable app wakes up, runs SportsWidget.js for ~1 second]
│
├─ Step 1: Fetch the noticeboard.
│          `fetch("https://atharv-garg.github.io/sports-widget-data/feed.json")`
│          The phone hits Cloudflare's nearest edge server,
│          gets the JSON, parses it into a JavaScript object.
│
├─ Step 2: Pick the right data section.
│          The widget's "Parameter" setting is "ufc", so the script
│          reads `feed.ufc.next` and `feed.ufc.upcoming`.
│
├─ Step 3: Build a WidgetKit widget using Scriptable's JS API.
│          - Add header text "UFC · FIGHT NIGHT"
│          - Add headline "Kape vs Horiguchi"
│          - Add date row
│          - Add 5 main card rows
│          - Add UP NEXT section with 6 upcoming events
│          - Set tap URL to ufc.com event page
│
└─ Step 4: Hand the constructed widget back to iOS.
            iOS captures it as a static image and displays it on your home screen.
```

The script finishes. Scriptable goes back to sleep. Your widget tile now shows the freshly-rendered data.

### 3:30 PM onwards — Static again

The widget keeps showing what just got rendered. Nothing else happens until either iOS decides to refresh again (~25-30 min later) or you tap the tile (which opens Safari to ufc.com, not Scriptable).

---

## Where each piece of code physically lives and runs

| Code | Where it physically lives | Where it runs | When it runs |
|---|---|---|---|
| `scrapers/f1.py` | GitHub repo | GitHub's temporary VMs | Once an hour |
| `scrapers/ufc.py` | GitHub repo | GitHub's temporary VMs | Once an hour |
| `scrapers/ufc_espn.py` | GitHub repo | GitHub's temporary VMs | Only when ufc.py fails |
| `scrapers/build.py` | GitHub repo | GitHub's temporary VMs | Once an hour |
| `docs/feed.json` | GitHub repo + Pages CDN | Nowhere — it's just a file | Read on demand |
| `docs/SportsWidget.js` | Your iPhone (inside Scriptable's storage) | Your iPhone | Every 25-30 min |

Two important things to notice:

1. **The Python and JavaScript never run on the same computer.** Python runs only on GitHub. JavaScript runs only on your phone.
2. **`SportsWidget.js` is hosted on Pages, but Pages doesn't run it.** Pages serves it like any other file. The reason it's hosted there at all is so you can install it on your phone by visiting the URL in Safari and copying the text into Scriptable. After install, your phone has its own local copy; it doesn't fetch the script again.

---

## Why we set it up this way

If you tried to put everything on the phone (had the phone scrape ufc.com directly), three problems:
- The phone would scrape ufc.com 24+ times a day, possibly getting blocked
- If ufc.com changes its HTML, every user has to update their script manually
- Every device wastes battery on the same work

By doing all the scraping on GitHub once an hour, all phones share the same result. If ufc.com changes its HTML, fix the Python on Windows, push, and *every phone in the world gets the fix on the next refresh without doing anything*.

If you tried to put everything on a real server (running 24/7 somewhere), you'd pay for hosting. GitHub Actions + Pages + Cloudflare let us achieve the same thing for $0 because we're using each service exactly the way it was designed.

---

## The 60-second mental model

When something doesn't look right in the widget, ask yourself:

1. **Is the noticeboard wrong?** Open `https://atharv-garg.github.io/sports-widget-data/feed.json` in your browser and read it. If the JSON itself has wrong data, the problem is in the Python scrapers — fix `scrapers/ufc.py` on Windows and push.

2. **Is the noticeboard right but the widget shows stale info?** The JSON is fresh but iOS hasn't refreshed yet. Remove and re-add the widget to force a refresh.

3. **Is the widget rendering wrong data on top of correct JSON?** The bug is in `SportsWidget.js`. Fix that script and re-paste it into Scriptable.

That diagnostic flow works because the noticeboard is the boundary between the two halves of the system. Either the data is wrong before the noticeboard (server problem) or after the noticeboard (phone problem). Never both.
