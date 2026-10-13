/* QualityLens: hospital quality & patient-safety command center */
const D = window.QL_DATA, M = D.measures, AS_OF = D.meta.as_of;
const KEYS = Object.keys(M);
const QS = uniq(KEYS.flatMap((k) => M[k].quarterly.map((q) => q.q))).sort();
const HARM = ["No harm", "Minor", "Moderate", "Severe", "Permanent", "Death"];
const TYPE_COLORS = ["#0f8b8d", "#4f7cff", "#e8a317", "#d23f3f", "#8b5cf6", "#14b8a6", "#f97316", "#64748b", "#ec4899", "#94a3b8"];
const state = { quarter: QS[QS.length - 1], ev: { unit: "all", type: "all", harm: "all", status: "all", q: "", page: 0, sort: ["occurred", -1] }, ab: { tab: "board", who: "all", meas: "all" }, ins: { sev: "all" }, mkey: "fall_rate", mview: "spc" };
const overrides = { ev: store.get("ev", {}), case: store.get("case", {}), find: store.get("find", {}) };

const ICON = {
  overview: '<path d="M3 12l9-8 9 8M5 10v10h5v-6h4v6h5V10"/>', measures: '<path d="M4 19V9m6 10V5m6 14v-7m4 7H2"/>',
  events: '<path d="M12 3l9 16H3zM12 10v4m0 3h.01"/>', abstraction: '<path d="M9 5h10M9 12h10M9 19h10M4 5l1 1 2-2M4 12l1 1 2-2M4 19l1 1 2-2"/>',
  ed: '<path d="M3 12h4l2-7 4 14 2-7h6"/>', insights: '<path d="M9 18h6M10 21h4M12 3a6 6 0 00-4 10.5c.7.7 1 1.5 1 2.5h6c0-1 .3-1.8 1-2.5A6 6 0 0012 3z"/>',
  data: '<path d="M4 6c0-1.7 3.6-3 8-3s8 1.3 8 3-3.6 3-8 3-8-1.3-8-3zm0 0v12c0 1.7 3.6 3 8 3s8-1.3 8-3V6M4 12c0 1.7 3.6 3 8 3s8-1.3 8-3"/>', about: '<path d="M12 8h.01M11 12h1v5h1M12 21a9 9 0 100-18 9 9 0 000 18z"/>',
};
const ico = (n) => `<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round">${ICON[n]}</svg>`;
const PAGES = [["overview", "Overview"], ["measures", "Measures"], ["events", "Safety Events"], ["abstraction", "Abstraction & Reporting"], ["ed", "ED Flow"], ["insights", "Insights"], ["data", "Data & Quality"], ["about", "About"]];

/* ---------- derived data ---------- */
const qv = (m, q) => m.quarterly.find((x) => x.q === q)?.v;
function stats(m, q = state.quarter) {
  const i = QS.indexOf(q), cur = qv(m, q), prior = qv(m, QS[i - 1]), yago = qv(m, QS[i - 4]);
  const delta = cur != null && prior != null ? cur - prior : null;
  const better = delta == null ? null : (delta < 0) === (m.direction === "lower");
  return { cur, prior, yago, delta, better, status: rag(cur, m), series: m.quarterly.filter((x) => QS.indexOf(x.q) <= i).slice(-8).map((x) => x.v) };
}
const effStatus = (e) => overrides.ev[e.id]?.status || e.status;
const isOpen = (e) => effStatus(e) !== "Closed";
const caseStatus = (c) => overrides.case[c.id] || c.status;
const daysBetween = (a, b) => Math.round((new Date(b) - new Date(a)) / 864e5);

/* ---------- shell ---------- */
function shell() {
  const openEv = D.events.filter(isOpen).length;
  $("#app").innerHTML = `
  <aside class="side" id="side">
    <div class="brand"><div class="logo">Q</div><div><b>QualityLens</b><span>Quality · Risk · Patient Safety</span></div></div>
    <nav class="nav" id="nav">${PAGES.map(([k, l]) => `<a data-nav="${k}" href="#/${k}">${ico(k === "overview" ? "overview" : k)}<span>${l}</span>${k === "events" ? `<span class="badge" id="evbadge">${openEv}</span>` : ""}</a>`).join("")}</nav>
    <div class="sp"></div>
    <div class="foot">${esc(D.meta.hospital)}<br>Extract ${fmtDate(AS_OF)}</div>
  </aside>
  <div class="main">
    <div class="top">
      <button class="ibtn menu" data-act="menu" aria-label="Menu">☰</button>
      <div class="search" data-act="palette"><svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path d="M20 20l-3.5-3.5"/></svg><span>Search measures, events, findings…</span><kbd>⌘K</kbd></div>
      <div class="sp"></div><span class="asof">Data as of ${fmtDate(AS_OF)}</span>
      <button class="ibtn" data-act="print" title="Print this page">⎙ Print</button>
      <button class="ibtn" data-act="theme" id="themebtn" title="Toggle theme">◐</button>
    </div>
    <main id="page" class="page"></main>
  </div>
  <div class="scrim" id="scrim" data-act="close"></div><aside class="drawer" id="drawer"></aside>
  <div class="pal" id="pal"><input id="palin" placeholder="Jump to a page, measure, finding or event ID…" autocomplete="off"><div class="res" id="palres"></div></div>`;
}

function route() {
  const [, page = "overview", arg] = location.hash.split("/");
  const fn = { overview, measures, events, abstraction, ed, insights, data, about }[page] || overview;
  if (page === "measures" && arg && M[arg]) state.mkey = arg;
  $("#page").innerHTML = ""; fn(); window.scrollTo(0, 0);
  $$("#nav a").forEach((a) => a.classList.toggle("on", a.dataset.nav === (page in { overview: 1, measures: 1, events: 1, abstraction: 1, ed: 1, insights: 1, data: 1, about: 1 } ? page : "overview")));
  $("#side").classList.remove("open");
}

const header = (title, sub, extra = "") => `<div class="ph"><div><h1>${title}</h1><p>${sub}</p></div><div class="sp"></div>${extra}</div>`;
const qSelect = () => `<select class="sel" data-act="quarter">${QS.slice().reverse().map((q) => `<option value="${q}" ${q === state.quarter ? "selected" : ""}>${qlabel(q)}</option>`).join("")}</select>`;

/* ---------- OVERVIEW ---------- */
function tile(m) {
  const s = stats(m), arrow = s.delta == null ? "–" : s.better ? "▲" : "▼";
  const dtxt = s.delta == null ? "n/a" : `${s.delta > 0 ? "+" : ""}${m.key === "mortality_oe" ? s.delta.toFixed(2) : s.delta.toFixed(1)} vs prior`;
  const ph = s.cur == null;
  return `<div class="tile ${s.status}" data-act="measure" data-key="${m.key}" tabindex="0">
    <div class="lab">${esc(shortLabel(m))}</div>
    <div class="val">${ph ? "–" : fmtVal(s.cur, m)}<small>${unitLabel(m)}</small></div>
    <div class="row"><span class="${s.better == null ? "flat" : s.better ? "up" : "down"}">${arrow} ${dtxt}</span>${sparkline(s.series)}</div>
    <div class="row"><span>Target ${m.direction === "lower" ? "≤" : "≥"} ${m.target}</span><span class="pill ${s.status}">${s.status}</span></div></div>`;
}

function overview() {
  const all = KEYS.filter((k) => D.scorecard_order.some((d) => d.keys.includes(k))).map((k) => M[k]);
  const cnt = { Green: 0, Amber: 0, Red: 0 }; all.forEach((m) => cnt[stats(m).status]++);
  const q = state.quarter, qs = D.events.filter((e) => quarterOf(e.occurred) === q);
  const openAll = D.events.filter(isOpen), old = openAll.filter((e) => daysBetween(e.reported || e.occurred, AS_OF) > 30).length;
  const ab = stats(M.abstraction_on_time);
  const top = D.findings.filter((f) => f.severity === "High" || f.severity === "Medium").slice(0, 4);
  const sigN = new Set(D.signals.map((s) => s.measure_key)).size;
  $("#page").innerHTML = header("Quality & Patient Safety", `${esc(D.meta.hospital)} · executive overview`, qSelect()) + `
  <div class="hero">
    <div class="card"><h3>Scorecard status · ${qlabel(q)}</h3><div class="sub">${all.length} measures against illustrative targets</div>
      <div class="donutwrap">${donut([{ v: cnt.Green, c: "var(--g)", l: "Green" }, { v: cnt.Amber, c: "var(--a)", l: "Amber" }, { v: cnt.Red, c: "var(--r)", l: "Red" }])}
      <div class="legend"><div><span class="dot" style="background:var(--g)"></span><b>${cnt.Green}</b> on target</div><div><span class="dot" style="background:var(--a)"></span><b>${cnt.Amber}</b> close to target</div><div><span class="dot" style="background:var(--r)"></span><b>${cnt.Red}</b> off target</div><div style="color:var(--mut);margin-top:6px">${sigN} measures have had a control-chart signal</div></div></div></div>
    <div class="grid g4" style="grid-template-columns:repeat(auto-fit,minmax(170px,1fr))">
      <div class="card stat"><span>Safety events reported</span><b data-count="${qs.length}">${qs.length}</b><span>${qlabel(q)}</span></div>
      <div class="card stat"><span>Open events</span><b>${openAll.length}</b><span style="color:${old ? "var(--r)" : "var(--mut)"}">${old} open &gt; 30 days</span></div>
      <div class="card stat"><span>Abstraction on time</span><b>${nf(ab.cur, 0)}%</b><span>target ≥ ${M.abstraction_on_time.target}%</span></div>
      <div class="card stat"><span>Serious harm events</span><b>${qs.filter((e) => e.harm >= 3).length}</b><span>harm level 3+ · ${qlabel(q)}</span></div></div></div>
  ${D.scorecard_order.map((dom) => `<div class="sec"><h2>${dom.domain}</h2></div><div class="grid g4">${dom.keys.map((k) => tile(M[k])).join("")}</div>`).join("")}
  <div class="sec"><h2>Needs attention</h2></div><div class="card">${top.map((f) => findCard(f, true)).join("")}<a href="#/insights" style="font-weight:600">See all ${D.findings.length} findings →</a></div>`;
}
const quarterOf = (d) => `${d.slice(0, 4)}Q${Math.ceil(+d.slice(5, 7) / 3)}`;

function findCard(f, compact = false) {
  const id = f.title, done = overrides.find[id];
  return `<div class="find ${f.severity} ${done ? "done" : ""}"><h4><span class="pill ${f.severity === "High" ? "Red" : "Amber"}">${f.severity}</span>${esc(f.title)}<span class="pill gray">${esc(f.domain)}</span></h4>
  <p><b>Evidence.</b> ${esc(f.evidence)}</p>${compact ? "" : `<p><b>Suggested action.</b> ${esc(f.action)}</p><p><label style="cursor:pointer"><input type="checkbox" data-act="found" data-id="${esc(id)}" ${done ? "checked" : ""}> Reviewed by committee</label></p>`}</div>`;
}

/* ---------- MEASURE DETAIL ---------- */
function measureDetail(m) {
  const s = stats(m), sigs = m.monthly.filter((p) => p.s);
  const rel = D.findings.filter((f) => f.evidence.toLowerCase().includes(shortLabel(m).toLowerCase().split(" ")[0]) || f.title.toLowerCase().includes(m.key.split("_")[0]));
  let extra = "";
  if (m.key === "fall_rate" || m.key === "med_event_rate") {
    const src = m.key === "fall_rate" ? D.falls_unit : D.meds_unit, units = Object.keys(D.meta.units), qsx = QS.filter((q) => q >= "2025Q1");
    extra = `<div class="card" style="margin-top:12px"><h3>By unit and quarter (per 1,000 patient days)</h3><div class="sub">Where is it happening? Darker = higher.</div>${heatmap(units, qsx, (u, q) => { const r = src.find((x) => x.unit_id === u && x.quarter === q); return r ? { v: r.per_1000_pd, label: r.per_1000_pd.toFixed(1), tip: `<b>${D.meta.units[u]} · ${qlabel(q)}</b><br>${r.events} events / ${nf(r.patient_days, 0)} patient days` } : null; }, { rowLabel: (u) => D.meta.units[u], colLabel: qlabel, cw: 62, lw: 120, labels: true })}</div>`;
  }
  if (m.key === "vte_ppx_rate") {
    const units = uniq(D.vte.map((v) => v.unit_id));
    extra = `<div class="card" style="margin-top:12px"><h3>By unit and admission day</h3><div class="sub">Weekend admissions to one unit stand out.</div>${heatmap(units, ["Weekday", "Weekend"], (u, c) => { const r = D.vte.find((x) => x.unit_id === u && x.admit_day_type === c); return { v: -r.value, label: r.value.toFixed(1) + "%", tip: `<b>${D.meta.units[u]} · ${c}</b><br>${r.value.toFixed(1)}% (n=${r.denominator})` }; }, { rowLabel: (u) => D.meta.units[u], cw: 90, lw: 120, labels: true })}</div>`;
  }
  if (m.key.startsWith("readmit")) {
    extra = `<div class="card" style="margin-top:12px"><h3>Readmission rate by diagnosis group (monthly)</h3><div class="sub">Small monthly denominators: read the trend, not single points.</div>
    ${["readmit_30d_hf", "readmit_30d_pn", "readmit_30d_ami"].map((k, i) => `<div style="margin:4px 0"><b style="font-size:12px">${{ readmit_30d_hf: "Heart failure", readmit_30d_pn: "Pneumonia", readmit_30d_ami: "AMI" }[k]}</b>${sparkline(D.readmit_by_dx[k].map((x) => x.v), 600, 34)}</div>`).join("")}</div>`;
  }
  return `<div class="dh"><h2>${esc(shortLabel(m))}</h2><span class="pill ${s.status}">${s.status}</span></div>
  <div class="grid g4" style="grid-template-columns:repeat(4,1fr);margin-bottom:12px">
   <div class="card stat"><span>${qlabel(state.quarter)}</span><b>${fmtVal(s.cur, m)}</b></div><div class="card stat"><span>Prior quarter</span><b>${fmtVal(s.prior, m)}</b></div>
   <div class="card stat"><span>Year ago</span><b>${fmtVal(s.yago, m)}</b></div><div class="card stat"><span>Target</span><b>${m.target}</b></div></div>
  <div class="card"><div class="seg" style="float:right"><button data-act="mview" data-v="spc" class="${state.mview === "spc" ? "on" : ""}">Control chart</button><button data-act="mview" data-v="q" class="${state.mview === "q" ? "on" : ""}">Quarterly</button></div>
   <h3>${state.mview === "spc" ? "Monthly control chart" : "Quarterly result"}</h3><div class="sub">${state.mview === "spc" ? "Centre line and 3σ limits frozen on the first 12 months (shaded). Red points signal." : "Bars vs target (dotted line)."}</div>
   ${state.mview === "spc" ? spcChart(m) : barChart(m.quarterly.map((q) => ({ l: qlabel(q.q), v: q.v, cur: q.q === state.quarter })), m.target, { nd: m.key === "mortality_oe" ? 2 : 1 })}</div>
  ${extra}
  <div class="grid g2" style="margin-top:12px"><div class="card"><h3>Definition</h3><dl class="kv"><dt>What</dt><dd>${esc(m.definition)}</dd><dt>Numerator</dt><dd>${esc(m.numerator)}</dd><dt>Denominator</dt><dd>${esc(m.denominator)}</dd><dt>Chart type</dt><dd>${{ p: "p-chart (proportion)", u: "u-chart (rate per exposure)", i: "XmR (individuals)" }[m.kind]}</dd></dl></div>
  <div class="card"><h3>Signals (${sigs.length})</h3>${sigs.length ? `<div style="display:flex;gap:6px;flex-wrap:wrap">${sigs.map((p) => `<span class="pill ${(m.direction === "lower" ? p.v > p.c : p.v < p.c) ? "Red" : "info"}" data-tip="${[p.s & 1 && "beyond limit", p.s & 2 && "shift", p.s & 4 && "trend"].filter(Boolean).join(", ")}">${mlabel(p.m)}</span>`).join("")}</div><p class="sub" style="margin-top:8px">Red = signal in the adverse direction.</p>` : `<div class="empty">No signals: this measure is in statistical control.</div>`}</div></div>
  ${rel.length ? `<div class="sec"><h2>Related findings</h2></div><div class="card">${rel.slice(0, 2).map((f) => findCard(f, true)).join("")}</div>` : ""}`;
}

function measures() {
  const m = M[state.mkey];
  $("#page").innerHTML = header("Measures", "Explore any measure: control chart, quarterly view, drill-downs and definition") + `<div style="display:grid;grid-template-columns:270px 1fr;gap:16px" class="mlayout">
   <div class="card" style="padding:10px;align-self:start;position:sticky;top:76px;max-height:calc(100vh - 100px);overflow:auto">${D.scorecard_order.map((d) => `<div style="font-size:11px;text-transform:uppercase;letter-spacing:.07em;color:var(--mut);margin:10px 8px 4px">${d.domain}</div>${d.keys.map((k) => { const s = stats(M[k]); return `<a data-act="msel" data-key="${k}" style="display:flex;align-items:center;gap:8px;padding:7px 8px;border-radius:9px;cursor:pointer;color:var(--ink);${k === state.mkey ? "background:var(--panel2);font-weight:650;" : ""}"><span class="dot" style="background:var(--${{ Green: "g", Amber: "a", Red: "r" }[s.status]})"></span><span style="flex:1;font-size:13px">${esc(shortLabel(M[k]))}</span><b style="font-size:12px">${fmtVal(s.cur, M[k])}</b></a>`; }).join("")}`).join("")}</div>
   <div id="mdetail">${measureDetail(m)}</div></div>`;
  if (innerWidth < 900) $(".mlayout").style.gridTemplateColumns = "1fr";
}

/* ---------- SAFETY EVENTS ---------- */
function filteredEvents() {
  const f = state.ev, ql = f.q.toLowerCase();
  let rows = D.events.filter((e) => (f.unit === "all" || e.unit === f.unit) && (f.type === "all" || e.type === f.type) && (f.harm === "all" || (f.harm === "3" ? e.harm >= 3 : e.harm === +f.harm))
    && (f.status === "all" || (f.status === "Open" ? isOpen(e) : effStatus(e) === f.status)) && (!ql || `${e.id} ${e.type} ${e.unit} ${e.cause || ""} ${overrides.ev[e.id]?.assignee || ""}`.toLowerCase().includes(ql)));
  const [k, dir] = f.sort; rows.sort((a, b) => ((a[k] ?? "") > (b[k] ?? "") ? 1 : -1) * dir); return rows;
}
function events() {
  const f = state.ev, units = Object.keys(D.meta.units), types = uniq(D.events.map((e) => e.type)).sort();
  $("#page").innerHTML = header("Safety Events", "Reported events, harm, review status and follow-up. Click any row for the timeline and actions.") + `
  <div class="filters"><div class="seg">${["all", ...units].map((u) => `<button data-act="evf" data-k="unit" data-v="${u}" class="${f.unit === u ? "on" : ""}">${u === "all" ? "All units" : u}</button>`).join("")}</div>
   <select class="sel" data-act="evsel" data-k="type"><option value="all">All types</option>${types.map((t) => `<option ${f.type === t ? "selected" : ""}>${esc(t)}</option>`).join("")}</select>
   <select class="sel" data-act="evsel" data-k="harm"><option value="all">Any harm</option><option value="0" ${f.harm === "0" ? "selected" : ""}>No harm</option><option value="3" ${f.harm === "3" ? "selected" : ""}>Serious (3+)</option></select>
   <select class="sel" data-act="evsel" data-k="status"><option value="all">Any status</option>${["Open", "Under Review", "Closed"].map((s) => `<option ${f.status === s ? "selected" : ""}>${s}</option>`).join("")}</select>
   <input class="inp" id="evq" placeholder="Search ID, type, unit, root cause…" value="${esc(f.q)}" style="min-width:230px"></div><div id="evbody"></div>`;
  $("#evq").addEventListener("input", (e) => { state.ev.q = e.target.value; state.ev.page = 0; eventsBody(); });
  eventsBody();
}
function eventsBody() {
  const rows = filteredEvents(), months = D.meta.months, f = state.ev;
  const types = uniq(D.events.map((e) => e.type)).sort();
  const series = Object.fromEntries(types.map((t) => [t, months.map((m) => rows.filter((e) => e.type === t && e.occurred.slice(0, 7) === m).length)]));
  const act = Object.fromEntries(types.map((t, i) => [t, i])).constructor; // noop
  const openN = rows.filter(isOpen).length, serious = rows.filter((e) => e.harm >= 3).length, lags = rows.map((e) => e.lag).filter((x) => x != null).sort((a, b) => a - b);
  const within = rows.filter((e) => e.lag != null && e.lag <= 24).length / (lags.length || 1) * 100;
  const harmCounts = HARM.map((h, i) => ({ l: h, v: rows.filter((e) => e.harm === i).length, c: i >= 3 ? "var(--r)" : i === 2 ? "var(--a)" : "var(--brand)" }));
  const units = Object.keys(D.meta.units), um = (u, m) => D.unit_month.find((x) => x.unit === u && x.month === m);
  const per = 25, pages = Math.max(1, Math.ceil(rows.length / per)); f.page = Math.min(f.page, pages - 1);
  const th = (k, l, n) => `<th class="s ${n ? "n" : ""}" data-act="sort" data-k="${k}">${l}${f.sort[0] === k ? (f.sort[1] > 0 ? " ▲" : " ▼") : ""}</th>`;
  $("#evbody").innerHTML = `<div class="grid g4" style="margin-bottom:14px">
    <div class="card stat"><span>Events (filtered)</span><b>${rows.length}</b><span>of ${D.events.length} in window</span></div><div class="card stat"><span>Open / under review</span><b>${openN}</b></div>
    <div class="card stat"><span>Serious harm (3+)</span><b>${serious}</b></div><div class="card stat"><span>Reported within 24h</span><b>${nf(within, 0)}%</b><span>median lag ${lags.length ? nf(lags[Math.floor(lags.length / 2)], 1) : "–"} h</span></div></div>
   <div class="grid g2"><div class="card"><h3>Events by month and type</h3><div class="sub">Hover for counts</div>${stacked(months, series, TYPE_COLORS)}<div style="display:flex;gap:10px;flex-wrap:wrap;margin-top:6px">${types.map((t, i) => `<span style="font-size:11.5px;color:var(--mut)"><span class="dot" style="background:${TYPE_COLORS[i % 10]}"></span> ${esc(t)}</span>`).join("")}</div></div>
   <div class="card"><h3>Harm level</h3><div class="sub">AHRQ-style scale, simplified</div>${hbars(harmCounts, Math.max(...harmCounts.map((h) => h.v), 1))}
    <h3 style="margin-top:14px">Events per 1,000 patient days · unit × month</h3>${heatmap(units, months.filter((_, i) => i % 2 === 0), (u, m) => { const r = um(u, m); if (!r) return null; const rows2 = D.events.filter((e) => e.unit === u && e.occurred.slice(0, 7) === m).length; return { v: (1000 * rows2) / r.pd, tip: `<b>${u} · ${mlabel(m)}</b><br>${rows2} events (${((1000 * rows2) / r.pd).toFixed(1)} per 1,000 pd)` }; }, { cw: 24, ch: 20, lw: 44, colLabel: (m) => mlabel(m).slice(0, 3) })}</div></div>
   <div class="card" style="margin-top:14px;padding:6px 8px"><table class="tbl"><thead><tr>${th("id", "ID")}${th("occurred", "Occurred")}${th("type", "Type")}${th("unit", "Unit")}${th("harm", "Harm", 1)}${th("lag", "Report lag (h)", 1)}${th("status", "Status")}<th>Assignee</th></tr></thead><tbody>
   ${rows.slice(f.page * per, f.page * per + per).map((e) => { const st = effStatus(e); return `<tr class="row" data-act="event" data-id="${e.id}"><td>#${e.id}</td><td>${fmtDate(e.occurred)}</td><td>${esc(e.type)}</td><td>${e.unit}</td><td class="n"><span class="pill ${e.harm >= 3 ? "Red" : e.harm >= 1 ? "Amber" : "gray"}">${e.harm}</span></td><td class="n">${e.lag ?? "–"}</td><td><span class="pill ${st === "Closed" ? "Green" : st === "Open" ? "Red" : "info"}">${st}</span></td><td>${esc(overrides.ev[e.id]?.assignee || "–")}</td></tr>`; }).join("") || `<tr><td colspan="8" class="empty">No events match.</td></tr>`}</tbody></table>
   <div style="display:flex;justify-content:space-between;align-items:center;padding:10px"><span class="sub">${rows.length ? f.page * per + 1 : 0}–${Math.min(rows.length, f.page * per + per)} of ${rows.length}</span><div><button class="btn sec2" data-act="pg" data-d="-1" ${f.page ? "" : "disabled"}>‹ Prev</button> <button class="btn sec2" data-act="pg" data-d="1" ${f.page < pages - 1 ? "" : "disabled"}>Next ›</button></div></div></div>`;
}
function eventDetail(id) {
  const e = D.events.find((x) => x.id === +id), ov = overrides.ev[id] || {}, st = effStatus(e);
  const lagDays = e.reported ? ((new Date(e.reported.replace(" ", "T")) - new Date(e.occurred.replace(" ", "T"))) / 864e5).toFixed(1) : null;
  return `<div class="dh"><h2>Event #${e.id}</h2><span class="pill ${e.harm >= 3 ? "Red" : e.harm >= 1 ? "Amber" : "gray"}">Harm ${e.harm} · ${HARM[e.harm]}</span></div>
  <div class="card"><dl class="kv"><dt>Type</dt><dd>${esc(e.type)}</dd><dt>Unit</dt><dd>${esc(D.meta.units[e.unit])}</dd><dt>Reporter</dt><dd>${esc(e.role)}</dd><dt>Encounter</dt><dd>${e.enc ? "#" + e.enc : "not linked (visitor/staff)"}</dd><dt>Root cause</dt><dd>${esc(e.cause || "pending review")}</dd></dl></div>
  <div class="card" style="margin-top:12px"><h3>Timeline</h3><div class="tl"><div><b>Occurred</b><br>${fmtDate(e.occurred)} ${e.occurred.slice(11)}</div><div class="${e.reported ? "" : "off"}"><b>Reported</b><br>${e.reported ? `${fmtDate(e.reported)} (${e.lag} h after event${e.lag > 24 ? ", late" : ""})` : "no report time recorded"}</div><div class="${e.reviewed || st === "Closed" ? "" : "off"}"><b>${st === "Closed" ? "Closed" : "Review"}</b><br>${e.reviewed ? fmtDate(e.reviewed) : st === "Closed" ? "closed (demo action)" : `pending · ${e.reported ? daysBetween(e.reported, AS_OF) : "?"} days since report`}</div></div></div>
  <div class="card" style="margin-top:12px"><h3>Follow-up (demo, saved in this browser)</h3><div class="filters" style="margin-top:8px"><select class="sel" id="asg"><option value="">Assign reviewer…</option>${["A. Rivera", "B. Okafor", "C. Nguyen", "D. Patel"].map((a) => `<option ${ov.assignee === a ? "selected" : ""}>${a}</option>`).join("")}</select>
  <button class="btn" data-act="evassign" data-id="${id}">Save assignee</button>${st !== "Closed" ? `<button class="btn sec2" data-act="evclose" data-id="${id}">Mark closed</button>` : `<button class="btn sec2" data-act="evreopen" data-id="${id}">Reopen</button>`}</div></div>`;
}

/* ---------- ABSTRACTION ---------- */
function abstraction() {
  const a = state.ab, tabs = [["board", "Case board"], ["work", "Workload"], ["sub", "Public reporting"], ["irr", "Quality of abstraction"]];
  $("#page").innerHTML = header("Abstraction & Public Reporting", "Case selection, abstractor workload, submission calendar and data validation") + `<div class="filters"><div class="seg">${tabs.map(([k, l]) => `<button data-act="abtab" data-v="${k}" class="${a.tab === k ? "on" : ""}">${l}</button>`).join("")}</div></div><div id="abbody"></div>`;
  abBody();
}
function abBody() {
  const a = state.ab, who = uniq(D.cases.map((c) => c.abstractor)).sort(), meas = uniq(D.cases.map((c) => c.measure)).sort();
  const late = (c) => caseStatus(c) !== "Completed" && c.due < AS_OF;
  if (a.tab === "board") {
    const cutoff = new Date(new Date(AS_OF) - 30 * 864e5).toISOString().slice(0, 10);
    let cs = D.cases.filter((c) => (a.who === "all" || c.abstractor === a.who) && (a.meas === "all" || c.measure === a.meas) && (caseStatus(c) !== "Completed" || (c.completed && c.completed >= cutoff) || overrides.case[c.id]));
    const cols = ["Not Started", "In Progress", "Completed"];
    const card = (c) => { const L = late(c), dd = daysBetween(AS_OF, c.due); return `<div class="kc ${L ? "late" : ""}" draggable="true" data-id="${c.id}"><div class="t"><b>${c.measure.replace("_", " ")}</b><span class="av" data-tip="${esc(c.abstractor)}">${c.abstractor.split(" ").map((x) => x[0]).join("")}</span></div><div class="sub" style="margin:2px 0 0">Case #${c.id} · enc ${c.enc}</div><div style="font-size:12px;color:${L ? "var(--r)" : "var(--mut)"}">${caseStatus(c) === "Completed" ? "done " + fmtDate(c.completed || AS_OF) : L ? `${-dd} days overdue` : `due in ${dd} days`}${c.second ? " · 2nd review" : ""}</div></div>`; };
    $("#abbody").innerHTML = `<div class="filters"><select class="sel" data-act="abf" data-k="who"><option value="all">All abstractors</option>${who.map((w) => `<option ${a.who === w ? "selected" : ""}>${w}</option>`).join("")}</select><select class="sel" data-act="abf" data-k="meas"><option value="all">All measures</option>${meas.map((w) => `<option ${a.meas === w ? "selected" : ""}>${w}</option>`).join("")}</select><span class="sub">Drag cards between columns · changes persist in this browser (demo)</span></div>
    <div class="board">${cols.map((col) => { const items = cs.filter((c) => caseStatus(c) === col); return `<div class="col" data-col="${col}"><h4><span>${col}</span><span>${items.length}${col !== "Completed" ? ` · ${items.filter(late).length} late` : " (last 30 days)"}</span></h4>${items.slice(0, 60).map(card).join("") || '<div class="empty">Nothing here</div>'}</div>`; }).join("")}</div>`;
    $$(".kc").forEach((el) => el.addEventListener("dragstart", (e) => e.dataTransfer.setData("text/plain", el.dataset.id)));
    $$(".col").forEach((el) => { el.addEventListener("dragover", (e) => { e.preventDefault(); el.classList.add("over"); }); el.addEventListener("dragleave", () => el.classList.remove("over")); el.addEventListener("drop", (e) => { e.preventDefault(); overrides.case[e.dataTransfer.getData("text/plain")] = el.dataset.col; store.set("case", overrides.case); toast(`Moved to ${el.dataset.col}`); abBody(); }); });
  } else if (a.tab === "work") {
    $("#abbody").innerHTML = `<div class="grid g2"><div class="card"><h3>Open cases by abstractor</h3><div class="sub">Overdue shown in red</div>${hbars(D.workload.map((w) => ({ l: w.abstractor, v: w.open_cases, t: `${w.open_cases} (${w.overdue} late)`, c: w.overdue ? "var(--r)" : "var(--brand)" })), Math.max(...D.workload.map((w) => w.open_cases), 1))}</div>
    <div class="card"><h3>Throughput</h3><div class="sub">Average days from case selection to completion</div>${hbars(D.workload.map((w) => ({ l: w.abstractor, v: w.avg_days_to_complete, t: w.avg_days_to_complete + " d" })), Math.max(...D.workload.map((w) => w.avg_days_to_complete)) * 1.1)}</div></div>
    <div class="card" style="margin-top:14px"><h3>Backlog signal</h3><div class="sub">On-time completion by selection month</div>${spcChart(M.abstraction_on_time, { h: 220 })}</div>`;
  } else if (a.tab === "sub") {
    const qs = uniq(D.submissions.map((s) => s.quarter)).sort(), ms = uniq(D.submissions.map((s) => s.measure_id));
    const cls = { "Submitted on time": "Green", "Submitted late": "Amber", OVERDUE: "Red", "Not yet due": "gray" };
    $("#abbody").innerHTML = `<div class="card"><h3>Quarterly submission calendar</h3><div class="sub">Due date = quarter end + 120 days (illustrative). Hover for dates.</div><div style="overflow:auto"><table class="tbl"><thead><tr><th>Measure</th>${qs.map((q) => `<th>${qlabel(q)}</th>`).join("")}</tr></thead><tbody>${ms.map((m) => `<tr><td><b>${m.replace("_", " ")}</b></td>${qs.map((q) => { const s = D.submissions.find((x) => x.measure_id === m && x.quarter === q); return `<td><span class="pill ${cls[s.status]}" data-tip="Due ${fmtDate(s.due)}<br>${s.sub ? "Submitted " + fmtDate(s.sub) + `<br>${s.records_submitted} records` : "not submitted"}">${s.status === "Submitted on time" ? "✓ on time" : s.status === "Submitted late" ? "late" : s.status === "OVERDUE" ? "overdue" : "pending"}</span></td>`; }).join("")}</tr>`).join("")}</tbody></table></div></div>`;
  } else {
    const all = D.irr.find((x) => x.measure_id === "ALL");
    $("#abbody").innerHTML = `<div class="grid g4"><div class="card stat"><span>Second-review agreement</span><b>${nf(all.percent_agreement, 1)}%</b><span>${all.pairs} case pairs</span></div><div class="card stat"><span>Cohen's kappa</span><b>${nf(all.kappa, 2)}</b><span>above 0.8 = strong agreement</span></div></div>
    <div class="grid g2" style="margin-top:14px"><div class="card"><h3>Inter-rater agreement by measure</h3>${hbars(D.irr.filter((x) => x.measure_id !== "ALL").map((x) => ({ l: x.measure_id.replace("_", " "), v: x.percent_agreement, t: `${nf(x.percent_agreement, 1)}% · κ ${nf(x.kappa, 2)}` })), 100)}</div>
    <div class="card"><h3>Abstracted vs EHR-derived</h3><div class="sub">Validation, similar in spirit to CMS data validation</div>${hbars(D.validation.map((x) => ({ l: x.measure_id.replace("_", " "), v: x.agreement_pct, t: `${nf(x.agreement_pct, 1)}% (${x.cases})` })), 100)}</div></div>`;
  }
}

/* ---------- ED ---------- */
function ed() {
  const dows = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], hrs = [...Array(24).keys()], mode = state.edmode || "los";
  const get = (d, h) => D.ed_heat.find((x) => x.dow === d && x.hr === h);
  const best = D.ed_heat.reduce((a, b) => (b.med > a.med ? b : a));
  $("#page").innerHTML = header("ED Flow", "When and where throughput breaks down") + `
  <div class="card"><div class="seg" style="float:right"><button data-act="edm" data-v="los" class="${mode === "los" ? "on" : ""}">Median LOS</button><button data-act="edm" data-v="n" class="${mode === "n" ? "on" : ""}">Volume</button></div>
  <h3>${mode === "los" ? "Median arrival-to-departure (min) by arrival day and hour" : "Discharged ED visits by arrival day and hour"}</h3><div class="sub">Longest median: <b>${dows[best.dow]} ${String(best.hr).padStart(2, "0")}:00</b> at ${Math.round(best.med)} min. Reporting window, discharged patients only.</div>
  <div style="overflow:auto">${heatmap(dows.map((_, i) => i), hrs, (d, h) => { const x = get(d, h); if (!x) return null; return { v: mode === "los" ? x.med : x.n, label: mode === "los" ? Math.round(x.med) : "", tip: `<b>${dows[d]} ${String(h).padStart(2, "0")}:00</b><br>median ${Math.round(x.med)} min<br>${x.n} visits` }; }, { rowLabel: (i) => dows[i], colLabel: (h) => h, cw: 36, ch: 30, lw: 44, labels: mode === "los" })}</div></div>
  <div class="grid g3" style="margin-top:14px">${["ed_los_median", "ed_boarding_median", "ed_lwbs_rate"].map((k) => `<div class="card"><h3>${esc(shortLabel(M[k]))}</h3><div class="sub">${qlabel(state.quarter)}: <b>${fmtVal(stats(M[k]).cur, M[k])}</b> · target ${M[k].target}</div>${spcChart(M[k], { h: 200, w: 520 })}</div>`).join("")}</div>`;
}

/* ---------- INSIGHTS ---------- */
function insights() {
  const sev = state.ins.sev, fs = D.findings.filter((f) => sev === "all" || f.severity === sev);
  $("#page").innerHTML = header("Insights", "Findings from my analysis: each number is computed at build time, with a suggested action", `<div class="seg">${["all", "High", "Medium"].map((s) => `<button data-act="insev" data-v="${s}" class="${sev === s ? "on" : ""}">${s === "all" ? "All" : s}</button>`).join("")}</div>`) + `
  <div class="card">${fs.map((f) => findCard(f)).join("") || '<div class="empty">No findings.</div>'}</div>
  <div class="sec"><h2>Control-chart signals</h2></div><div class="card" style="padding:6px 8px"><table class="tbl"><thead><tr><th>Measure</th><th>First signal</th><th>Last signal</th><th class="n">Signal months</th><th class="n">Adverse</th><th>Peak</th></tr></thead><tbody>
  ${D.signals.map((s) => `<tr class="row" data-act="measure" data-key="${s.measure_key}"><td>${esc(s.label)}</td><td>${mlabel(s.first_signal)}</td><td>${mlabel(s.last_signal)}</td><td class="n">${s.signal_months}</td><td class="n">${s.adverse_months}</td><td>${mlabel(s.peak_month)}</td></tr>`).join("")}</tbody></table></div>`;
}

/* ---------- DATA & QUALITY ---------- */
function data() {
  const v = D.meta.volumes, mx = Math.max(...D.dq.filter((r) => r.rule_id !== "ENC-00").map((r) => r.rows_affected), 1);
  $("#page").innerHTML = header("Data & Quality", "How the numbers are produced, and proof that they can be trusted") + `
  <div class="card"><h3>Pipeline</h3><div class="steps" style="margin-top:8px">${["Data generator (seeded)", "Raw CSV extracts", "10 cleaning rules (logged)", "SQLite database", "SQL measure views", "SPC + findings engine", "Dashboard · Excel · PDF · this app"].map((s, i, a) => `<span class="st">${s}</span>${i < a.length - 1 ? '<span class="ar">→</span>' : ""}`).join("")}</div></div>
  <div class="grid g4" style="margin-top:14px"><div class="card stat"><span>Inpatient encounters</span><b>${nf(v.encounters, 0)}</b></div><div class="card stat"><span>ED visits</span><b>${nf(v.ed_visits, 0)}</b></div><div class="card stat"><span>Safety events</span><b>${nf(v.events, 0)}</b></div><div class="card stat"><span>Automated tests</span><b>${D.tests.count}</b><span>all passing at build</span></div></div>
  <div class="grid g2" style="margin-top:14px"><div class="card"><h3>Cleaning rules and rows fixed</h3><div class="sub">I injected these defects into the raw data on purpose; a test confirms the pipeline finds exactly those.</div>${D.dq.filter((r) => r.rule_id !== "ENC-00").map((r) => `<div style="margin:9px 0"><div style="display:flex;justify-content:space-between;gap:10px"><span><b>${r.rule_id}</b> ${esc(r.description)}</span><b>${r.rows_affected}</b></div><div class="bar-h"><i style="width:${(r.rows_affected / mx) * 100}%"></i></div><div class="sub" style="margin:2px 0 0">${esc(r.action)}</div></div>`).join("")}</div>
  <div class="card"><h3>How testing works</h3><ul style="padding-left:18px;color:var(--mut)"><li><b style="color:var(--ink)">Independent recomputation:</b> every SQL measure is recalculated in pandas and compared to 1e-9.</li><li><b style="color:var(--ink)">Cleaning vs ground truth:</b> rows flagged equal defects injected.</li><li><b style="color:var(--ink)">SPC unit tests:</b> known limits, shift and trend boundaries.</li><li><b style="color:var(--ink)">Detection tests:</b> planted signals must be rediscovered unaided.</li><li><b style="color:var(--ink)">Mutation check:</b> breaking the readmission SQL makes the suite fail.</li></ul>
  <h3 style="margin-top:14px">Limits</h3><ul style="padding-left:18px;color:var(--mut)"><li>Simplified, non-official measure logic and a simple mortality model.</li><li>No PHI controls or audit trail implemented.</li></ul></div></div>`;
}

function about() {
  $("#page").innerHTML = header("About QualityLens", "My portfolio project: quality reporting for a fictional community hospital") + `<div class="card"><p>I built QualityLens to turn raw operational data into committee-ready quality reporting: scorecards, statistical process control, safety-event follow-up, chart-abstraction workflow and public-reporting status. Built by Naveen Kumar Kovi.</p>
  <p>Targets are internal targets I set for the project. I simplified the measure logic from public quality-measure concepts.</p>
  <h3>Other deliverables</h3><p><a href="../outputs/dashboard.html">Static dashboard</a> · <a href="../outputs/Quality_Committee_Pack.xlsx">Excel committee pack</a> · <a href="../outputs/Quality_Brief.pdf">PDF brief</a> · <a href="../README.md">README</a> · <a href="../docs/case_study.md">Case study</a></p>
  <h3>Demo actions</h3><p>Assigning or closing events, moving abstraction cards and marking findings reviewed are saved only in this browser's local storage. <a data-act="reset" style="cursor:pointer">Reset demo state</a></p></div>`;
}

/* ---------- interactions ---------- */
function openDrawer(html) { $("#drawer").innerHTML = `<button class="ibtn x" data-act="close">✕</button>${html}`; $("#drawer").classList.add("on"); $("#scrim").classList.add("on"); $("#drawer").scrollTop = 0; }
function closeDrawer() { $("#drawer").classList.remove("on"); $("#scrim").classList.remove("on"); }
function toast(t) { const el = document.createElement("div"); el.className = "toast"; el.textContent = t; document.body.appendChild(el); setTimeout(() => el.remove(), 1800); }
function setTheme(t) { document.documentElement.dataset.theme = t; store.set("theme", t); }

document.addEventListener("click", (e) => {
  const t = e.target.closest("[data-act]"); if (!t) return; const act = t.dataset.act;
  const rerender = () => route();
  switch (act) {
    case "measure": state.mview = state.mview; openDrawer(measureDetail(M[t.dataset.key])); $("#drawer").dataset.key = t.dataset.key; break;
    case "close": closeDrawer(); break;
    case "msel": state.mkey = t.dataset.key; history.replaceState(null, "", `#/measures/${state.mkey}`); measures(); break;
    case "mview": state.mview = t.dataset.v; if ($("#drawer").classList.contains("on") && $("#drawer").dataset.key) { openDrawer(measureDetail(M[$("#drawer").dataset.key])); } else measures(); break;
    case "menu": $("#side").classList.toggle("open"); break;
    case "theme": setTheme(document.documentElement.dataset.theme === "dark" ? "light" : "dark"); break;
    case "print": window.print(); break;
    case "palette": palette(true); break;
    case "evf": state.ev[t.dataset.k] = t.dataset.v; state.ev.page = 0; events(); break;
    case "sort": { const k = t.dataset.k; state.ev.sort = [k, state.ev.sort[0] === k ? -state.ev.sort[1] : 1]; eventsBody(); break; }
    case "pg": state.ev.page += +t.dataset.d; eventsBody(); break;
    case "event": openDrawer(eventDetail(t.dataset.id)); break;
    case "evassign": { const v = $("#asg").value; overrides.ev[t.dataset.id] = { ...(overrides.ev[t.dataset.id] || {}), assignee: v }; store.set("ev", overrides.ev); toast("Assignee saved"); eventsBody(); openDrawer(eventDetail(t.dataset.id)); break; }
    case "evclose": overrides.ev[t.dataset.id] = { ...(overrides.ev[t.dataset.id] || {}), status: "Closed" }; store.set("ev", overrides.ev); toast("Event closed (demo)"); badge(); eventsBody(); openDrawer(eventDetail(t.dataset.id)); break;
    case "evreopen": overrides.ev[t.dataset.id] = { ...(overrides.ev[t.dataset.id] || {}), status: "Open" }; store.set("ev", overrides.ev); badge(); eventsBody(); openDrawer(eventDetail(t.dataset.id)); break;
    case "abtab": state.ab.tab = t.dataset.v; abstraction(); break;
    case "edm": state.edmode = t.dataset.v; ed(); break;
    case "insev": state.ins.sev = t.dataset.v; insights(); break;
    case "reset": ["ev", "case", "find"].forEach((k) => { overrides[k] = {}; store.set(k, {}); }); toast("Demo state reset"); badge(); break;
  }
});
document.addEventListener("change", (e) => {
  const t = e.target.closest("[data-act]"); if (!t) return;
  if (t.dataset.act === "quarter") { state.quarter = t.value; route(); }
  if (t.dataset.act === "evsel") { state.ev[t.dataset.k] = t.value; state.ev.page = 0; eventsBody(); }
  if (t.dataset.act === "abf") { state.ab[t.dataset.k] = t.value; abBody(); }
  if (t.dataset.act === "found") { overrides.find[t.dataset.id] = t.checked; store.set("find", overrides.find); t.closest(".find").classList.toggle("done", t.checked); }
});
const badge = () => { const b = $("#evbadge"); if (b) b.textContent = D.events.filter(isOpen).length; };

/* command palette */
function palette(open) {
  const el = $("#pal"), inp = $("#palin"), res = $("#palres");
  if (!open) { el.classList.remove("on"); return; }
  el.classList.add("on"); inp.value = ""; inp.focus(); draw("");
  function items(q) {
    q = q.toLowerCase().trim(); const out = [];
    PAGES.forEach(([k, l]) => out.push({ t: l, s: "Page", go: () => (location.hash = `#/${k}`) }));
    KEYS.forEach((k) => out.push({ t: M[k].label, s: "Measure", go: () => { location.hash = `#/measures/${k}`; } }));
    D.findings.forEach((f) => out.push({ t: f.title, s: "Finding", go: () => (location.hash = "#/insights") }));
    if (/^#?\d{4,}$/.test(q)) { const ev = D.events.find((x) => String(x.id) === q.replace("#", "")); if (ev) out.unshift({ t: `Event #${ev.id} · ${ev.type} · ${ev.unit}`, s: "Event", go: () => { location.hash = "#/events"; setTimeout(() => openDrawer(eventDetail(ev.id)), 50); } }); }
    return out.filter((i) => !q || i.t.toLowerCase().includes(q) || i.s.toLowerCase().includes(q)).slice(0, 9);
  }
  let cur = [], sel = 0;
  function draw(q) { cur = items(q); sel = 0; res.innerHTML = cur.map((i, n) => `<div class="it ${n === sel ? "sel" : ""}" data-n="${n}">${esc(i.t)}<small>${i.s}</small></div>`).join("") || '<div class="empty">No matches</div>'; }
  inp.oninput = () => draw(inp.value);
  inp.onkeydown = (e) => {
    if (e.key === "ArrowDown") sel = Math.min(sel + 1, cur.length - 1); else if (e.key === "ArrowUp") sel = Math.max(sel - 1, 0);
    else if (e.key === "Enter" && cur[sel]) { palette(false); cur[sel].go(); return; } else if (e.key === "Escape") { palette(false); return; } else return;
    $$(".it", res).forEach((x, n) => x.classList.toggle("sel", n === sel)); e.preventDefault();
  };
  res.onclick = (e) => { const it = e.target.closest(".it"); if (it) { palette(false); cur[+it.dataset.n].go(); } };
}
document.addEventListener("keydown", (e) => {
  if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === "k") { e.preventDefault(); palette(true); }
  else if (e.key === "Escape") { closeDrawer(); palette(false); }
});
document.addEventListener("mousedown", (e) => { if (!e.target.closest("#pal") && !e.target.closest(".search")) $("#pal")?.classList.remove("on"); });

/* boot */
setTheme(store.get("theme", matchMedia("(prefers-color-scheme: dark)").matches ? "dark" : "light"));
shell(); window.addEventListener("hashchange", route); route();
