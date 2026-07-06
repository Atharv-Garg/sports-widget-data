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
  const fm = FileManager.local();
  const cachePath = fm.joinPath(fm.cacheDirectory(), "sportswidget_feed.json");
  try {
    // Minute-resolution cache-buster defeats stale CDN / URLSession caches.
    const req = new Request(`${FEED_URL}?t=${Math.floor(Date.now() / 60000)}`);
    req.timeoutInterval = 10;
    const feed = await req.loadJSON();
    // Save last-known-good (overwrites previous) + drop photos no longer needed.
    try {
      fm.writeString(cachePath, JSON.stringify(feed));
      pruneImgCache(fm, heroImgUrls(feed));
    } catch (e) {}
    return feed;
  } catch (e) {
    // Offline: fall back to the last cached feed instead of showing nothing.
    if (fm.fileExists(cachePath)) {
      try { return JSON.parse(fm.readString(cachePath)); } catch (e2) {}
    }
    throw e;  // no cache yet (first run) -> nothing to show
  }
}

// Stable filename for a photo URL; only the 2 main-event photos are cached.
function imgKey(url) {
  let h = 5381;
  for (let i = 0; i < url.length; i++) h = ((h * 33) ^ url.charCodeAt(i)) >>> 0;
  return "sw_img_" + h.toString(16) + ".png";
}
function heroImgUrls(feed) {
  const m = (feed.ufc?.next?.main_card || [])[0];
  return m ? [m.red_img, m.blue_img].filter(Boolean) : [];
}
function pruneImgCache(fm, keepUrls) {
  try {
    const dir = fm.cacheDirectory();
    const keep = new Set(keepUrls.map(imgKey));
    for (const name of fm.listContents(dir)) {
      if (name.startsWith("sw_img_") && !keep.has(name)) {
        try { fm.remove(fm.joinPath(dir, name)); } catch (e) {}
      }
    }
  } catch (e) {}
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
const fmtDateTime = iso => iso ? fmt(iso, "EEE d MMM · h:mm a") : "—";  // "Sat 27 Jun · 7:30 PM"
const fmtDayDateTime = iso => iso ? fmt(iso, "d MMM · h:mm a")  : "—";  // "27 Jun · 7:30 PM" (no weekday, fits one row)
const fmtFullDate = iso => iso ? fmt(iso, "EEE d MMM")          : "—";  // "Sat 20 Jun"
const fmtTime     = iso => iso ? fmt(iso, "h:mm a")             : "—";  // "5:30 AM"
const fmtShortDay = iso => iso ? fmt(iso, "d MMM")              : "—";  // "27 Jun"

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

// --- UFC data helpers -----------------------------------------------------
const WEIGHT_ABBR = {
  "Strawweight": "STW", "Flyweight": "FLW", "Bantamweight": "BW",
  "Featherweight": "FW", "Lightweight": "LW", "Welterweight": "WW",
  "Middleweight": "MW", "Light Heavyweight": "LHW", "Heavyweight": "HW",
  "Catchweight": "CW", "Openweight": "OW",
};

function abbrevWeight(wc) {
  // "Lightweight Bout" -> "LW", "Women's Flyweight" -> "WFLW",
  // "Welterweight Title Bout" -> "WW" (the ★ already marks it a title fight).
  // Unknown divisions fall back to the stripped full name so nothing breaks.
  let s = stripBout(wc || "");
  s = s.replace(/\s+(Title|Championship)\s*$/i, "").trim();
  let women = false;
  s = s.replace(/^Women['’]s\s+/i, () => { women = true; return ""; }).trim();
  const a = WEIGHT_ABBR[s];
  if (!a) return s;
  return women ? `W${a}` : a;
}

// Crop a tall fighter cutout to its top fraction (head & torso) so the hero
// reads big without the lower-body whitespace eating vertical budget.
function cropTop(img, frac) {
  const w = img.size.width, h = img.size.height;
  const dc = new DrawContext();
  dc.size = new Size(w, Math.round(h * frac));
  dc.respectScreenScale = true;
  dc.opaque = false;
  dc.drawImageAtPoint(img, new Point(0, 0));  // bottom is clipped by dc.size
  return dc.getImage();
}

async function loadImg(url) {
  if (!url) return null;
  const fm = FileManager.local();
  const path = fm.joinPath(fm.cacheDirectory(), imgKey(url));
  try {
    const r = new Request(url);
    r.timeoutInterval = 8;
    const img = await r.loadImage();
    try { fm.writeImage(path, img); } catch (e) {}   // cache on success
    return img;
  } catch (e) {
    if (fm.fileExists(path)) {                         // offline -> cached photo
      try { return fm.readImage(path); } catch (e2) {}
    }
    return null;  // no cache -> caller falls back to text
  }
}

function addPhoto(stack, img, targetH) {
  const wi = stack.addImage(img);
  const s = targetH / img.size.height;
  wi.imageSize = new Size(img.size.width * s, targetH);
}

// Fixed-width, borderless weight-class label (accent color, no chip/pill
// background) so fighter names still line up in a column without the boxy
// look a filled pill gives at this size.
function weightLabel(row, text) {
  const c = row.addStack();
  c.size = new Size(34, 15);
  c.centerAlignContent();
  addText(c, text.toUpperCase(), Font.boldSystemFont(10), ACCENT_UFC);
}

// A fixed-width photo cell for the hero row, matching the width of its
// corresponding heroFighter() name column so photo and name always align.
function photoCol(parent, width, img) {
  const col = parent.addStack();
  col.size = new Size(width, 92);
  col.centerAlignContent();
  addPhoto(col, img, 92);
}

// The "VS" badge cell between the two hero photo columns.
function vsCol(parent, width, titleFight) {
  const col = parent.addStack();
  col.size = new Size(width, 92);
  col.centerAlignContent();
  addText(col, `VS${titleFight ? " ★" : ""}`, Font.boldSystemFont(13), ACCENT_UFC);
}

// One fighter's label column for the hero: rank · surname, odds beneath.
// Fixed-width (matches the photo column above it) and centred, so
// the name is always under its own photo regardless of name/odds length.
// Odds only render when a real value is available — a bare "-" (no
// sportsbook line posted yet) is treated the same as missing, and this same
// spot is where a real value will show up once one is published.
function heroFighter(parent, width, rank, name, odds) {
  const col = parent.addStack();
  col.layoutVertically();
  col.centerAlignContent();
  col.size = new Size(width, 0);
  const l1 = col.addStack();
  l1.layoutHorizontally();
  l1.centerAlignContent();
  if (rank) addText(l1, `${rank} `, Font.boldSystemFont(12), ACCENT_UFC);
  addText(l1, name, Font.semiboldSystemFont(15), TEXT_PRIMARY);
  if (odds && odds !== "-") {
    col.addSpacer(2);
    addText(col, odds, Font.caption1(), TEXT_SECONDARY);
  }
  return col;
}

// One "REST OF CARD" row: [weight] rank name v rank name … odds. Sized tight
// so ranks + surnames + odds all fit one line at the Large tile's ~310pt
// content width without truncation. Ranks are set in the accent color as a
// highlight, matching the hero treatment above.
function cardRow(widget, f) {
  const row = widget.addStack();
  row.layoutHorizontally();
  row.centerAlignContent();
  weightLabel(row, abbrevWeight(f.weight_class));
  row.addSpacer(8);
  if (f.red_rank) addText(row, `${f.red_rank} `, Font.boldSystemFont(11), ACCENT_UFC);
  addText(row, lastName(f.red), Font.mediumSystemFont(13), TEXT_PRIMARY);
  addText(row, " v ", Font.caption2(), TEXT_TERTIARY);
  if (f.blue_rank) addText(row, `${f.blue_rank} `, Font.boldSystemFont(11), ACCENT_UFC);
  addText(row, lastName(f.blue), Font.mediumSystemFont(13), TEXT_PRIMARY);
  if (f.title_fight) addText(row, " ★", Font.caption2(), ACCENT_UFC);
  row.addSpacer();
  const odds = [f.red_odds, f.blue_odds].filter(Boolean).join("/");
  if (odds) addText(row, odds, Font.caption2(), TEXT_SECONDARY);
}

// --- F1 Small -------------------------------------------------------------
const F1_KEEP_SMALL = new Set(["Sprint Quali", "Sprint", "Qualifying", "Race"]);
// Short labels so [name] + [date] fit on one row at the Small widget's width.
const F1_SESSION_LABEL = { "Sprint Quali": "Sprint Q", "Qualifying": "Quali" };

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
  // GP name on a single line so the session block below has a predictable
  // vertical budget. Shorten "Grand Prix" to "GP" (e.g. "British GP") so it
  // fits the Small widget without WidgetKit having to ellipsise it.
  const gpName = (ev.short_name || ev.name || "Grand Prix")
    .replace(/\bGrand Prix\b/i, "GP");
  addText(widget, gpName, Font.headline(), TEXT_PRIMARY, 1);

  widget.addSpacer(3);

  // Single line per session: label + "date · time" (no weekday — dropped so
  // the full string fits next to the label at a still-readable font size
  // without WidgetKit truncating it).
  const rows = (ev.sessions || []).filter(s => F1_KEEP_SMALL.has(s.type));
  for (let i = 0; i < rows.length; i++) {
    const s = rows[i];
    const isRace = s.type === "Race";
    const row = widget.addStack();
    row.centerAlignContent();
    addText(row, F1_SESSION_LABEL[s.type] || s.type,
            isRace ? Font.semiboldSystemFont(12) : Font.caption1(), isRace ? ACCENT_F1 : TEXT_PRIMARY);
    row.addSpacer();
    addText(row, fmtDayDateTime(s.start_ist),
            Font.systemFont(9), isRace ? ACCENT_F1 : TEXT_SECONDARY);
    if (i < rows.length - 1) widget.addSpacer(3);
  }
}

// --- UFC Large ------------------------------------------------------------
async function renderUFCLarge(widget, feed) {
  const ev = feed.ufc?.next;
  if (!ev) {
    addText(widget, "No upcoming UFC event", Font.subheadline(), TEXT_SECONDARY);
    return;
  }

  const card = ev.main_card || [];
  const main = card[0];

  // Header: "UFC <number|kind>" (e.g. "UFC 329", "UFC Fight Night") with the
  // suffix in accent color — no separate "PPV"/"FIGHT NIGHT" tag and no
  // fighter names, since those already appear under the hero photos below.
  // Same font/spacer budget as the old two-row header so total height is
  // unchanged.
  const head = widget.addStack();
  head.centerAlignContent();
  addText(head, "UFC ", Font.semiboldSystemFont(13), TEXT_PRIMARY);
  const nameMatch = /^UFC\s+(.+?):/.exec(ev.name || "");
  addText(head, nameMatch ? nameMatch[1] : (ev.kind || "Event"),
          Font.semiboldSystemFont(13), ACCENT_UFC, 1);

  widget.addSpacer(2);
  addText(widget, `${fmtFullDate(ev.main_card_start_ist)} · ${fmtTime(ev.main_card_start_ist)} IST`,
          Font.caption1(), TEXT_SECONDARY);
  widget.addSpacer(4);

  // Hero: main-event cutout photos (head & torso) + rank·name·odds beneath.
  // Falls back to a text headline when photos are missing (TBA / ESPN events).
  const redImg = main ? await loadImg(main.red_img) : null;
  const blueImg = main ? await loadImg(main.blue_img) : null;

  if (main && redImg && blueImg) {
    // Fixed-width columns (one per fighter, one for the VS badge) shared by
    // both the photo row and the name row below, so a fighter's name is
    // always centred under their own photo regardless of name/odds length —
    // no independent centring math between the two rows to drift apart.
    const colW = 130, vsW = 34;

    const photos = widget.addStack();
    photos.layoutHorizontally();
    photos.bottomAlignContent();
    photos.addSpacer();
    photoCol(photos, colW, cropTop(redImg, 0.58));
    vsCol(photos, vsW, main.title_fight);
    photoCol(photos, colW, cropTop(blueImg, 0.58));
    photos.addSpacer();
    widget.addSpacer(4);

    // Two fighters side by side, columns matching the photo row exactly so
    // alignment holds regardless of content. Odds render under the name only
    // when a real value is available (never a bare "-"); if ufc.com starts
    // publishing odds for this fight later, they'll appear here automatically.
    const labels = widget.addStack();
    labels.layoutHorizontally();
    labels.topAlignContent();
    labels.addSpacer();
    heroFighter(labels, colW, main.red_rank, lastName(main.red), main.red_odds);
    labels.addStack().size = new Size(vsW, 0);
    heroFighter(labels, colW, main.blue_rank, lastName(main.blue), main.blue_odds);
    labels.addSpacer();

    // …with weight class alone on a centred line beneath (VS now sits between
    // the photo columns above, not glued to this line).
    widget.addSpacer(3);
    const meta = widget.addStack();
    meta.layoutHorizontally();
    meta.centerAlignContent();
    meta.addSpacer();
    addText(meta, stripBout(main.weight_class).toUpperCase(), Font.boldSystemFont(10), ACCENT_UFC);
    meta.addSpacer();
  } else {
    // Text fallback: keep the headliner visible without photos.
    addText(widget, eventHeadline(ev.name), Font.headline(), TEXT_PRIMARY, 2);
  }

  divider(widget);

  // Rest of the main card (everything below the hero bout).
  addText(widget, "REST OF CARD", Font.caption2(), TEXT_TERTIARY);
  widget.addSpacer(3);
  const rest = card.slice(1, 5);
  for (const f of rest) cardRow(widget, f);
  if (!rest.length) {
    addText(widget, main ? "Full card TBA" : "Main card TBA",
            Font.caption1(), TEXT_TERTIARY);
  }

  divider(widget);

  addText(widget, "UP NEXT", Font.caption2(), TEXT_TERTIARY);
  widget.addSpacer(3);
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
  else                await renderUFCLarge(w, feed);

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
