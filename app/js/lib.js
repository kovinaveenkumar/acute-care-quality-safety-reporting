/* QualityLens helpers + dependency-free SVG charts */
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const MON = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const mlabel = (m) => `${MON[+m.slice(5, 7) - 1]} ${m.slice(2, 4)}`;
const qlabel = (q) => q.replace("Q", " Q");
const fmtDate = (d) => (d ? new Date(d.replace(" ", "T") + (d.length <= 10 ? "T00:00" : "")).toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric" }) : "–");
const nf = (v, d = 1) => (v == null || isNaN(v) ? "–" : Number(v).toLocaleString("en-US", { minimumFractionDigits: d, maximumFractionDigits: d }));
const uniq = (a) => [...new Set(a)];
const sum = (a) => a.reduce((x, y) => x + y, 0);
const store = {
  get(k, d) { try { const v = localStorage.getItem("ql_" + k); return v == null ? d : JSON.parse(v); } catch { return d; } },
  set(k, v) { try { localStorage.setItem("ql_" + k, JSON.stringify(v)); } catch {} },
};

function rag(v, m) {
  if (v == null) return "Gray";
  if (m.direction === "lower") return v <= m.target ? "Green" : v <= m.target * 1.10 ? "Amber" : "Red";
  return v >= m.target ? "Green" : v >= m.target * 0.93 ? "Amber" : "Red";
}
const unitLabel = (m) => (m.key === "mortality_oe" ? "" : /per 1,000/.test(m.label) ? "" : /\(%\)/.test(m.label) ? "%" : /\(min\)/.test(m.label) ? "min" : "");
const fmtVal = (v, m) => (m.key === "mortality_oe" ? nf(v, 2) : nf(v, /\(min\)/.test(m.label) ? 0 : 1));
const shortLabel = (m) => m.label.replace(/\s*\((%|min)\)/, "").replace(/^ED median /, "ED median ");

/* tooltip */
const tip = document.createElement("div"); tip.id = "tip"; document.body.appendChild(tip);
document.addEventListener("mousemove", (e) => {
  const t = e.target.closest?.("[data-tip]");
  if (!t) { tip.style.opacity = 0; return; }
  tip.innerHTML = t.getAttribute("data-tip");
  tip.style.opacity = 1;
  const w = tip.offsetWidth, x = Math.min(e.clientX + 14, innerWidth - w - 10);
  tip.style.left = x + "px"; tip.style.top = Math.min(e.clientY + 16, innerHeight - tip.offsetHeight - 10) + "px";
});

/* ---------- charts ---------- */
function scale(lo, hi, a, b) { const s = (b - a) / (hi - lo || 1); return (v) => a + (v - lo) * s; }

function sparkline(vals, w = 92, h = 26) {
  const v = vals.filter((x) => x != null); if (v.length < 2) return "";
  const lo = Math.min(...v), hi = Math.max(...v), X = scale(0, v.length - 1, 3, w - 3), Y = scale(lo, hi, h - 4, 4);
  const d = v.map((y, i) => `${i ? "L" : "M"}${X(i).toFixed(1)},${Y(y).toFixed(1)}`).join("");
  return `<svg class="spark" viewBox="0 0 ${w} ${h}"><path d="${d}"/><circle cx="${X(v.length - 1).toFixed(1)}" cy="${Y(v[v.length - 1]).toFixed(1)}" r="2.6"/></svg>`;
}

function donut(parts, size = 132, th = 18) {
  const tot = sum(parts.map((p) => p.v)) || 1, r = (size - th) / 2, c = 2 * Math.PI * r; let off = 0;
  const arcs = parts.map((p) => { const len = (p.v / tot) * c, s = `<circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="${p.c}" stroke-width="${th}" stroke-dasharray="${len} ${c - len}" stroke-dashoffset="${-off}" transform="rotate(-90 ${size / 2} ${size / 2})" data-tip="${p.l}: ${p.v}"/>`; off += len; return s; }).join("");
  return `<svg width="${size}" height="${size}" viewBox="0 0 ${size} ${size}"><circle cx="${size / 2}" cy="${size / 2}" r="${r}" fill="none" stroke="var(--line2)" stroke-width="${th}"/>${arcs}</svg>`;
}

/* statistical process control chart */
function spcChart(m, opts = {}) {
  const d = m.monthly, W = opts.w || 640, H = opts.h || 250, pl = 44, pr = 12, pt = 14, pb = 26;
  const nd = m.key === "mortality_oe" ? 2 : /\(min\)/.test(m.label) ? 0 : 1;
  const vals = d.flatMap((p) => [p.v, p.u, p.l]).concat([m.target]);
  let lo = Math.min(...vals), hi = Math.max(...vals); const pad = (hi - lo) * 0.07; lo -= pad; hi += pad;
  const X = scale(0, d.length - 1, pl, W - pr), Y = scale(lo, hi, H - pb, pt);
  let s = `<svg class="ch" viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(m.label)} control chart">`;
  for (let k = 0; k <= 4; k++) { const t = lo + ((hi - lo) * k) / 4; s += `<line class="grid" x1="${pl}" x2="${W - pr}" y1="${Y(t)}" y2="${Y(t)}"/><text x="${pl - 6}" y="${Y(t) + 3}" text-anchor="end">${t.toFixed(nd)}</text>`; }
  d.forEach((p, i) => { if (i % 3 === 0) s += `<text x="${X(i)}" y="${H - 8}" text-anchor="middle">${mlabel(p.m)}</text>`; });
  s += `<rect class="base" x="${pl}" y="${pt}" width="${X(Math.min(11, d.length - 1)) - pl}" height="${H - pb - pt}"/>`;
  s += `<text x="${pl + 4}" y="${pt + 10}" style="font-size:9.5px;opacity:.7">baseline</text>`;
  for (const k of ["u", "l"]) s += `<path class="lim" d="${d.map((p, i) => `${i ? "L" : "M"}${X(i)},${Y(p[k])}`).join("")}"/>`;
  s += `<path class="cl" d="${d.map((p, i) => `${i ? "L" : "M"}${X(i)},${Y(p.c)}`).join("")}"/>`;
  s += `<line class="tgt" x1="${pl}" x2="${W - pr}" y1="${Y(m.target)}" y2="${Y(m.target)}"/><text x="${W - pr - 2}" y="${Y(m.target) - 4}" text-anchor="end" style="fill:var(--brand);font-weight:700">target ${m.target}</text>`;
  s += `<path class="ln" d="${d.map((p, i) => `${i ? "L" : "M"}${X(i)},${Y(p.v)}`).join("")}"/>`;
  d.forEach((p, i) => {
    const why = [p.s & 1 && "beyond 3σ limit", p.s & 2 && "8-point shift", p.s & 4 && "6-point trend"].filter(Boolean).join(", ");
    const tipTxt = `<b>${mlabel(p.m)}</b><br>${p.v.toFixed(nd)}${p.n != null && p.d ? `<br><span style='opacity:.8'>${nf(p.n, 0)} / ${nf(p.d, 0)}</span>` : ""}${why ? `<br><span style='color:#ff9b9b'>⚠ ${why}</span>` : ""}`;
    s += `<circle class="pt ${p.s ? "s" : ""}" cx="${X(i)}" cy="${Y(p.v)}" r="${p.s ? 4.4 : 3}"/><rect class="hit" x="${X(i) - 10}" y="${pt}" width="20" height="${H - pb - pt}" data-tip="${esc(tipTxt)}"/>`;
  });
  return s + "</svg>";
}

function barChart(items, target, o = {}) { // items [{l, v, cur}]
  const W = o.w || 640, H = o.h || 190, pl = 40, pr = 10, pt = 14, pb = 26, nd = o.nd ?? 1;
  const vals = items.map((i) => i.v).concat(target != null ? [target] : []);
  const hi = Math.max(...vals) * 1.12, lo = 0, Y = scale(lo, hi, H - pb, pt), bw = ((W - pl - pr) / items.length) * 0.6, step = (W - pl - pr) / items.length;
  let s = `<svg class="ch" viewBox="0 0 ${W} ${H}">`;
  for (let k = 0; k <= 3; k++) { const t = (hi * k) / 3; s += `<line class="grid" x1="${pl}" x2="${W - pr}" y1="${Y(t)}" y2="${Y(t)}"/><text x="${pl - 6}" y="${Y(t) + 3}" text-anchor="end">${t.toFixed(nd)}</text>`; }
  items.forEach((it, i) => { const x = pl + i * step + (step - bw) / 2; s += `<rect class="bar ${it.cur ? "cur" : ""}" x="${x}" y="${Y(it.v)}" width="${bw}" height="${Math.max(0, H - pb - Y(it.v))}" data-tip="<b>${esc(it.l)}</b><br>${it.v.toFixed(nd)}"/><text x="${x + bw / 2}" y="${H - 9}" text-anchor="middle">${esc(it.l)}</text>`; });
  if (target != null) s += `<line class="tgt" x1="${pl}" x2="${W - pr}" y1="${Y(target)}" y2="${Y(target)}"/>`;
  return s + "</svg>";
}

function stacked(months, series, colors, o = {}) { // series: {name: [vals per month]}
  const W = o.w || 640, H = o.h || 230, pl = 34, pr = 8, pt = 10, pb = 26, names = Object.keys(series);
  const tot = months.map((_, i) => sum(names.map((n) => series[n][i]))), hi = Math.max(...tot, 1) * 1.1, Y = scale(0, hi, H - pb, pt);
  const step = (W - pl - pr) / months.length, bw = step * 0.72;
  let s = `<svg class="ch" viewBox="0 0 ${W} ${H}">`;
  for (let k = 0; k <= 3; k++) { const t = (hi * k) / 3; s += `<line class="grid" x1="${pl}" x2="${W - pr}" y1="${Y(t)}" y2="${Y(t)}"/><text x="${pl - 5}" y="${Y(t) + 3}" text-anchor="end">${Math.round(t)}</text>`; }
  months.forEach((m, i) => {
    let acc = 0; const x = pl + i * step + (step - bw) / 2;
    names.forEach((n, j) => { const v = series[n][i]; if (!v) return; const y1 = Y(acc + v), y0 = Y(acc); s += `<rect x="${x}" y="${y1}" width="${bw}" height="${y0 - y1}" fill="${colors[j % colors.length]}" data-tip="<b>${mlabel(m)} · ${esc(n)}</b><br>${v} events"/>`; acc += v; });
    if (i % 3 === 0) s += `<text x="${x + bw / 2}" y="${H - 9}" text-anchor="middle">${mlabel(m)}</text>`;
  });
  return s + "</svg>";
}

function heatmap(rows, cols, cell, o = {}) { // cell(r,c) -> {v, label?, tip?}
  const cw = o.cw || 34, chh = o.ch || 26, lw = o.lw || 90, hh = 24, W = lw + cols.length * cw + 6, H = hh + rows.length * chh + 4;
  const all = rows.flatMap((r) => cols.map((c) => cell(r, c)?.v)).filter((v) => v != null), lo = Math.min(...all), hi = Math.max(...all);
  const color = o.color || ((v) => { const t = (v - lo) / (hi - lo || 1); return `color-mix(in srgb, #d23f3f ${Math.round(t * 78)}%, var(--panel2))`; });
  let s = `<svg class="ch hm" viewBox="0 0 ${W} ${H}" style="max-width:${Math.max(W, 300)}px">`;
  cols.forEach((c, j) => { s += `<text x="${lw + j * cw + cw / 2}" y="14" text-anchor="middle">${esc(o.colLabel ? o.colLabel(c) : c)}</text>`; });
  rows.forEach((r, i) => {
    s += `<text x="${lw - 8}" y="${hh + i * chh + chh / 2 + 3}" text-anchor="end">${esc(o.rowLabel ? o.rowLabel(r) : r)}</text>`;
    cols.forEach((c, j) => { const x = cell(r, c); if (!x || x.v == null) return; s += `<rect x="${lw + j * cw + 1}" y="${hh + i * chh + 1}" width="${cw - 2}" height="${chh - 2}" fill="${color(x.v)}" data-tip="${esc(x.tip || "")}"/>${o.labels ? `<text x="${lw + j * cw + cw / 2}" y="${hh + i * chh + chh / 2 + 3}" text-anchor="middle" style="fill:var(--ink);font-size:9.5px">${esc(x.label ?? "")}</text>` : ""}`; });
  });
  return s + "</svg>";
}

function hbars(items, max, color = "var(--brand)") {
  return items.map((i) => `<div style="display:grid;grid-template-columns:150px 1fr 54px;gap:10px;align-items:center;margin:6px 0"><span>${esc(i.l)}</span><div class="bar-h"><i style="width:${(i.v / max) * 100}%;background:${i.c || color}"></i></div><b style="text-align:right">${i.t ?? i.v}</b></div>`).join("");
}
