// SportsWidget — F1 + UFC native widget for iOS/macOS via Scriptable.
//
// Setup:
//   1. Put this file in iCloud Drive > Scriptable as "SportsWidget.js".
//   2. Edit FEED_URL below to your GitHub Pages JSON.
//   3. Add a Scriptable widget; long-press > Edit Widget; set Script = SportsWidget,
//      Parameter = "f1" or "ufc" (or leave blank for auto).
//   4. Tap the widget to expand into the full session/main-card list.

const FEED_URL = "https://atharv-garg.github.io/sports-widget-data/feed.json";

// --- Theme helpers --------------------------------------------------------
const ACCENT_F1  = Color.dynamic(new Color("#E10600"), new Color("#FF5C5C"));
const ACCENT_UFC = Color.dynamic(new Color("#D20A0A"), new Color("#FF7A1A"));
const TEXT_PRIMARY = Color.dynamic(Color.black(), Color.white());
const TEXT_SECONDARY = Color.dynamic(new Color("#3C3C43", 0.7), new Color("#EBEBF5", 0.7));
const TEXT_TERTIARY  = Color.dynamic(new Color("#3C3C43", 0.5), new Color("#EBEBF5", 0.5));

// --- Data -----------------------------------------------------------------
async function loadFeed() {
  // Cache-busting query param defeats both Scriptable's URLSession cache and
  // any stale Cloudflare edge cache on the Pages CDN — important right after
  // an event finishes, when the user wants to see the next one promptly.
  const req = new Request(`${FEED_URL}?t=${Math.floor(Date.now() / 60000)}`);
  req.timeoutInterval = 10;
  const data = await req.loadJSON();
  return data;
}

function pickSport(feed, requested) {
  if (requested === "f1" || requested === "ufc") return requested;
  // auto: whichever event is sooner
  const f1Start = feed.f1?.next?.sessions?.[0]?.start_utc;
  const ufcStart = feed.ufc?.next?.main_card_start_utc;
  if (!f1Start) return "ufc";
  if (!ufcStart) return "f1";
  return new Date(f1Start) <= new Date(ufcStart) ? "f1" : "ufc";
}

// --- Formatting -----------------------------------------------------------
function fmtIST(iso, withDate = true) {
  if (!iso) return "—";
  const d = new Date(iso);
  const df = new DateFormatter();
  df.locale = "en_IN";
  df.dateFormat = withDate ? "EEE d MMM, h:mm a" : "h:mm a";
  return df.string(d) + (withDate ? " IST" : "");
}

function fmtRelDay(iso) {
  if (!iso) return "";
  const d = new Date(iso);
  const today = new Date();
  const diff = Math.round((d - today) / 86400000);
  if (diff <= 0) return "Today";
  if (diff === 1) return "Tomorrow";
  if (diff < 7) {
    const df = new DateFormatter();
    df.dateFormat = "EEEE";
    return df.string(d);
  }
  const df = new DateFormatter();
  df.dateFormat = "EEE d MMM";
  return df.string(d);
}

// --- Widget rendering -----------------------------------------------------
function styled(stack, text, font, color) {
  const t = stack.addText(text);
  t.font = font;
  t.textColor = color;
  t.lineLimit = 1;
  return t;
}

function buildF1Widget(w, ev, family) {
  if (!ev) return buildEmpty(w, "No upcoming GP");
  const header = w.addStack();
  header.centerAlignContent();
  styled(header, "F1", Font.semiboldRoundedSystemFont(11), ACCENT_F1);
  header.addSpacer(6);
  styled(header, ev.flag_emoji || "", Font.systemFont(11), TEXT_SECONDARY);
  w.addSpacer(2);

  styled(w, ev.short_name || ev.name || "Grand Prix", Font.headline(), TEXT_PRIMARY);

  const race = (ev.sessions || []).find(s => s.type === "Race");
  if (family === "small") {
    w.addSpacer(2);
    styled(w, fmtRelDay(race?.start_ist), Font.subheadline(), TEXT_SECONDARY);
    styled(w, fmtIST(race?.start_ist, false), Font.caption1(), TEXT_TERTIARY);
    return;
  }

  w.addSpacer(4);
  const limit = family === "large" ? 6 : 3;
  for (const s of (ev.sessions || []).slice(0, limit)) {
    const row = w.addStack();
    row.layoutHorizontally();
    const label = row.addText(s.type);
    label.font = Font.subheadline();
    label.textColor = TEXT_PRIMARY;
    row.addSpacer();
    const time = row.addText(fmtIST(s.start_ist));
    time.font = Font.caption1();
    time.textColor = TEXT_SECONDARY;
  }
}

function buildUFCWidget(w, ev, family) {
  if (!ev) return buildEmpty(w, "No upcoming UFC event");
  const header = w.addStack();
  header.centerAlignContent();
  styled(header, "UFC · " + (ev.kind || "Event"), Font.semiboldRoundedSystemFont(11), ACCENT_UFC);
  w.addSpacer(2);

  styled(w, ev.name || "UFC Event", Font.headline(), TEXT_PRIMARY);

  if (family === "small") {
    w.addSpacer(2);
    styled(w, fmtRelDay(ev.main_card_start_ist), Font.subheadline(), TEXT_SECONDARY);
    styled(w, fmtIST(ev.main_card_start_ist, false), Font.caption1(), TEXT_TERTIARY);
    return;
  }

  styled(w, fmtIST(ev.main_card_start_ist), Font.subheadline(), TEXT_SECONDARY);
  w.addSpacer(4);

  const limit = family === "large" ? 5 : 2;
  const card = ev.main_card || [];
  if (card.length === 0) {
    styled(w, "Main card TBA", Font.caption1(), TEXT_TERTIARY);
    return;
  }
  for (const f of card.slice(0, limit)) {
    const row = w.addStack();
    row.layoutHorizontally();
    const names = row.addText(`${f.red}  vs  ${f.blue}`);
    names.font = Font.subheadline();
    names.textColor = TEXT_PRIMARY;
    names.lineLimit = 1;
    row.addSpacer();
    if (f.title_fight) {
      const tag = row.addText("★");
      tag.font = Font.caption2();
      tag.textColor = ACCENT_UFC;
    }
  }
}

function buildEmpty(w, msg) {
  const t = w.addText(msg);
  t.font = Font.subheadline();
  t.textColor = TEXT_SECONDARY;
}

async function makeWidget(feed, sport, family) {
  const w = new ListWidget();
  w.setPadding(14, 14, 14, 14);
  // Leave background unset on Mac so system vibrancy applies. On iOS, use a subtle tint.
  if (Device.isPhone() || Device.isPad()) {
    w.backgroundColor = Color.dynamic(new Color("#FFFFFF"), new Color("#1C1C1E"));
  }
  if (sport === "f1") buildF1Widget(w, feed.f1?.next, family);
  else buildUFCWidget(w, feed.ufc?.next, family);

  w.url = `scriptable:///run/${encodeURIComponent(Script.name())}?action=detail&sport=${sport}`;
  w.refreshAfterDate = new Date(Date.now() + 30 * 60 * 1000);
  return w;
}

// --- In-app detail (UITable) ---------------------------------------------
// Drill-down model: each detail view shows ONE event's full breakdown plus a
// tappable "Upcoming" list. Tapping an upcoming row re-renders the table to
// show that event. Reload-on-select is how Scriptable wires interactive rows.

function presentDetail(feed, sport, eventIndex = 0) {
  const table = new UITable();
  table.showSeparators = true;
  renderDetailInto(table, feed, sport, eventIndex);
  table.present();
}

function renderDetailInto(table, feed, sport, eventIndex) {
  table.removeAllRows();

  // Combined ordered list of all events (next + upcoming) for the sport.
  const events = sport === "f1"
    ? [feed.f1?.next, ...(feed.f1?.upcoming || [])].filter(Boolean)
    : [feed.ufc?.next, ...(feed.ufc?.upcoming || [])].filter(Boolean);

  if (events.length === 0) {
    table.addRow(_headerRow(sport === "f1" ? "No upcoming GP" : "No upcoming UFC event", ""));
    table.reload();
    return;
  }

  const idx = Math.max(0, Math.min(eventIndex, events.length - 1));
  const ev = events[idx];

  if (sport === "f1") {
    table.addRow(_headerRow(`${ev.flag_emoji || ""}  ${ev.name}`, ev.circuit || ev.location || ""));
    for (const s of ev.sessions || []) {
      table.addRow(_row(s.type, fmtIST(s.start_ist)));
    }
  } else {
    table.addRow(_headerRow(ev.name, `${ev.venue || ""}${ev.city ? " · " + ev.city : ""}`));
    table.addRow(_row("Main card", fmtIST(ev.main_card_start_ist)));
    if (!ev.main_card?.length) {
      table.addRow(_row("Main card TBA", ""));
    }
    for (const f of ev.main_card || []) {
      const title = `${f.red}  vs  ${f.blue}`;
      const sub = `${f.weight_class}${f.title_fight ? "  ★ Title" : ""}`;
      table.addRow(_row(title, sub));
    }
  }

  // Upcoming list — every other event becomes a tappable row that re-renders.
  const others = events.map((e, i) => ({ e, i })).filter(x => x.i !== idx);
  if (others.length) {
    table.addRow(_sectionRow("Upcoming"));
    for (const { e, i } of others) {
      const row = sport === "f1"
        ? _row(`${e.flag_emoji || ""}  ${e.short_name || e.name}`,
               fmtIST((e.sessions || []).find(s => s.type === "Race")?.start_ist))
        : _row(e.name, fmtIST(e.main_card_start_ist));
      row.dismissOnSelect = false;
      row.onSelect = () => renderDetailInto(table, feed, sport, i);
      table.addRow(row);
    }
  }

  // Sport switch — always available at the bottom.
  const switchRow = _sectionRow(sport === "f1" ? "Switch to UFC →" : "Switch to F1 →");
  switchRow.dismissOnSelect = false;
  switchRow.onSelect = () => renderDetailInto(table, feed, sport === "f1" ? "ufc" : "f1", 0);
  table.addRow(switchRow);

  table.reload();
}

function _row(title, subtitle) {
  const r = new UITableRow();
  r.height = 48;
  const c = r.addText(title, subtitle);
  c.titleFont = Font.subheadline();
  c.subtitleFont = Font.caption1();
  return r;
}
function _headerRow(title, subtitle) {
  const r = new UITableRow();
  r.height = 64;
  r.isHeader = true;
  const c = r.addText(title, subtitle);
  c.titleFont = Font.headline();
  c.subtitleFont = Font.caption1();
  return r;
}
function _sectionRow(label) {
  const r = new UITableRow();
  r.height = 36;
  const c = r.addText(label);
  c.titleFont = Font.semiboldRoundedSystemFont(13);
  c.titleColor = TEXT_SECONDARY;
  return r;
}
function presentEmpty(msg) {
  const t = new UITable();
  t.addRow(_headerRow(msg, ""));
  t.present();
}

// --- Entry point ----------------------------------------------------------
async function main() {
  const feed = await loadFeed();
  const requested = (args.widgetParameter || args.queryParameters?.sport || "auto").toLowerCase();
  const sport = pickSport(feed, requested);

  if (config.runsInWidget) {
    const w = await makeWidget(feed, sport, config.widgetFamily || "medium");
    Script.setWidget(w);
  } else if (args.queryParameters?.action === "detail") {
    presentDetail(feed, sport);
  } else {
    // Run from Scriptable app directly — preview + open detail.
    const preview = await makeWidget(feed, sport, "large");
    await preview.presentLarge();
    presentDetail(feed, sport);
  }
  Script.complete();
}

await main();
