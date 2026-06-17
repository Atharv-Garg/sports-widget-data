// SportsWidget — F1 + UFC widget for iOS/macOS via Scriptable.
//
// Designed for two specific surfaces:
//   - F1 on a SMALL widget   (parameter = "f1")
//   - UFC on a LARGE widget  (parameter = "ufc")
// Tapping either tile opens Safari directly to the official source page
// (formula1.com / ufc.com) — no Scriptable detour.

const FEED_URL = "https://atharv-garg.github.io/sports-widget-data/feed.json";

// --- Theme ----------------------------------------------------------------
const ACCENT_F1  = Color.dynamic(new Color("#E10600"), new Color("#FF5C5C"));
const ACCENT_UFC = Color.dynamic(new Color("#D20A0A"), new Color("#FF7A1A"));
const TEXT_PRIMARY   = Color.dynamic(Color.black(), Color.white());
const TEXT_SECONDARY = Color.dynamic(new Color("#3C3C43", 0.7), new Color("#EBEBF5", 0.7));
const TEXT_TERTIARY  = Color.dynamic(new Color("#3C3C43", 0.5), new Color("#EBEBF5", 0.5));
const DIVIDER        = Color.dynamic(new Color("#3C3C43", 0.18), new Color("#EBEBF5", 0.20));

// --- Data -----------------------------------------------------------------
async function loadFeed() {
  // Minute-resolution cache-buster defeats stale CDN / URLSession caches.
  const req = new Request(`${FEED_URL}?t=${Math.floor(Date.now() / 60000)}`);
  req.timeoutInterval = 10;
  return await req.loadJSON();
}

function pickSport(feed, requested) {
  if (requested === "f1" || requested === "ufc") return requested;
  const f1Start = feed.f1?.next?.sessions?.[0]?.start_utc;
  const ufcStart = feed.ufc?.next?.main_card_start_utc;
  if (!f1Start) return "ufc";
  if (!ufcStart) return "f1";
  return new Date(f1Start) <= new Date(ufcStart) ? "f1" : "ufc";
}

// --- Date formatting ------------------------------------------------------
function fmt(iso, pattern) {
  const df = new DateFormatter();
  df.locale = "en_IN";
  df.dateFormat = pattern;
  return df.string(new Date(iso));
}
const fmtDayTime  = iso => iso ? fmt(iso, "EEE h:mm a")    : "—";  // "Sun 6:30 PM"
const fmtFullDate = iso => iso ? fmt(iso, "EEE d MMM")     : "—";  // "Sat 20 Jun"
const fmtTime     = iso => iso ? fmt(iso, "h:mm a")        : "—";  // "5:30 AM"
const fmtShortDay = iso => iso ? fmt(iso, "d MMM")         : "—";  // "27 Jun"

// --- Helpers --------------------------------------------------------------
function addText(stack, text, font, color, lineLimit = 1) {
  const t = stack.addText(text);
  t.font = font;
  t.textColor = color;
  t.lineLimit = lineLimit;
  return t;
}

function divider(widget) {
  widget.addSpacer(6);
  const line = widget.addStack();
  line.size = new Size(0, 1);
  line.backgroundColor = DIVIDER;
  widget.addSpacer(6);
}

function lastName(fullName) {
  if (!fullName) return "";
  // Take last whitespace-separated token; skip generational suffixes.
  const parts = fullName.trim().split(/\s+/);
  let last = parts[parts.length - 1];
  if (/^(Jr\.?|Sr\.?|II|III|IV)$/i.test(last) && parts.length >= 2) {
    last = parts[parts.length - 2];
  }
  return last;
}

function eventHeadline(name) {
  // "UFC Fight Night: Kape vs Horiguchi" -> "Kape vs Horiguchi"
  // "UFC 329: McGregor vs Holloway 2"    -> "UFC 329: McGregor vs Holloway 2"
  // "UFC Abu Dhabi"                      -> "UFC Abu Dhabi"
  if (!name) return "";
  const colon = name.indexOf(":");
  if (colon < 0) return name;
  const prefix = name.slice(0, colon).trim();
  const tail = name.slice(colon + 1).trim();
  if (/^UFC\s+\d+/i.test(prefix)) return name;  // Keep numbered PPV prefix
  return tail || name;
}

function stripBout(wc) {
  return (wc || "").replace(/\s*Bout$/i, "").trim();
}

// --- F1 Small -------------------------------------------------------------
const F1_KEEP_SMALL = new Set(["Sprint", "Qualifying", "Race"]);

function renderF1Small(widget, ev) {
  if (!ev) {
    addText(widget, "No upcoming GP", Font.subheadline(), TEXT_SECONDARY);
    return;
  }

  const head = widget.addStack();
  head.centerAlignContent();
  addText(head, "F1", Font.semiboldRoundedSystemFont(11), ACCENT_F1);
  head.addSpacer(6);
  addText(head, ev.flag_emoji || "", Font.systemFont(11), TEXT_SECONDARY);

  widget.addSpacer(2);
  addText(widget, ev.short_name || ev.name || "Grand Prix",
          Font.headline(), TEXT_PRIMARY, 2);

  widget.addSpacer(6);

  const rows = (ev.sessions || []).filter(s => F1_KEEP_SMALL.has(s.type));
  for (const s of rows) {
    const row = widget.addStack();
    row.layoutHorizontally();
    addText(row, s.type === "Qualifying" ? "Quali" : s.type,
            Font.subheadline(), TEXT_PRIMARY);
    row.addSpacer();
    addText(row, fmtDayTime(s.start_ist), Font.caption1(), TEXT_SECONDARY);
  }
}

// --- UFC Large ------------------------------------------------------------
function renderUFCLarge(widget, feed) {
  const ev = feed.ufc?.next;
  if (!ev) {
    addText(widget, "No upcoming UFC event", Font.subheadline(), TEXT_SECONDARY);
    return;
  }

  const tag = widget.addStack();
  tag.centerAlignContent();
  addText(tag, `UFC · ${(ev.kind || "Event").toUpperCase()}`,
          Font.semiboldRoundedSystemFont(11), ACCENT_UFC);
  widget.addSpacer(2);

  addText(widget, eventHeadline(ev.name), Font.headline(), TEXT_PRIMARY, 2);
  widget.addSpacer(2);
  addText(widget, `${fmtFullDate(ev.main_card_start_ist)} · ${fmtTime(ev.main_card_start_ist)} IST`,
          Font.subheadline(), TEXT_SECONDARY);

  if (ev.venue || ev.city) {
    // The feed's `city` is "Las Vegas United States" style — drop the trailing
    // country to keep the venue line tight on one row.
    let city = (ev.city || "")
      .replace(/\s+(United States|United Kingdom)$/i, "")
      .replace(/\s+(Brazil|Mexico|Australia|Canada|Japan|China|Singapore|Germany|France|Spain|Italy|Russia|Azerbaijan|United Arab Emirates)$/i, "");
    const venueLine = [ev.venue, city].filter(Boolean).join(", ");
    addText(widget, venueLine, Font.caption1(), TEXT_TERTIARY);
  }

  divider(widget);

  addText(widget, "MAIN CARD", Font.caption2(), TEXT_TERTIARY);
  widget.addSpacer(2);
  for (const f of (ev.main_card || []).slice(0, 5)) {
    const row = widget.addStack();
    row.layoutHorizontally();
    row.centerAlignContent();
    const names = `${lastName(f.red)} vs ${lastName(f.blue)}${f.title_fight ? "  ★" : ""}`;
    addText(row, names, Font.subheadline(), TEXT_PRIMARY);
    row.addSpacer();
    addText(row, stripBout(f.weight_class), Font.caption1(), TEXT_SECONDARY);
  }
  if (!(ev.main_card || []).length) {
    addText(widget, "Main card TBA", Font.caption1(), TEXT_TERTIARY);
  }

  divider(widget);

  addText(widget, "UP NEXT", Font.caption2(), TEXT_TERTIARY);
  widget.addSpacer(2);
  const upcoming = (feed.ufc.upcoming || []).slice(0, 3);
  for (const u of upcoming) {
    const row = widget.addStack();
    row.layoutHorizontally();
    addText(row, fmtShortDay(u.main_card_start_ist),
            Font.caption1(), TEXT_SECONDARY);
    row.addSpacer(8);
    addText(row, eventHeadline(u.name), Font.caption1(), TEXT_PRIMARY);
  }
  if (!upcoming.length) {
    addText(widget, "No further events announced", Font.caption2(), TEXT_TERTIARY);
  }
}

// --- Tap target -----------------------------------------------------------
function tapURL(feed, sport) {
  if (sport === "f1") {
    return feed.f1?.next?.external_url
        || "https://www.formula1.com/en/racing/2026.html";
  }
  return feed.ufc?.next?.url
      || "https://www.ufc.com/events";
}

// --- Widget assembly ------------------------------------------------------
async function makeWidget(feed, sport) {
  const w = new ListWidget();
  w.setPadding(12, 14, 12, 14);
  if (Device.isPhone() || Device.isPad()) {
    w.backgroundColor = Color.dynamic(new Color("#FFFFFF"), new Color("#1C1C1E"));
  }
  if (sport === "f1") renderF1Small(w, feed.f1?.next);
  else                renderUFCLarge(w, feed);

  w.url = tapURL(feed, sport);
  w.refreshAfterDate = new Date(Date.now() + 30 * 60 * 1000);
  return w;
}

// --- Entry point ----------------------------------------------------------
async function main() {
  const feed = await loadFeed();
  const requested = (args.widgetParameter || "auto").toLowerCase();
  const sport = pickSport(feed, requested);

  if (config.runsInWidget) {
    const widget = await makeWidget(feed, sport);
    Script.setWidget(widget);
  } else {
    // Running from the Scriptable app — preview both tiles.
    const f1Preview = await makeWidget(feed, "f1");
    await f1Preview.presentSmall();
    const ufcPreview = await makeWidget(feed, "ufc");
    await ufcPreview.presentLarge();
  }
  Script.complete();
}

await main();
