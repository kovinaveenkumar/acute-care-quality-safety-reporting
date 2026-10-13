"""Self-contained HTML quality dashboard (no external assets; prints cleanly)."""
from __future__ import annotations

import html

import pandas as pd

from .charts import sparkline, spc_svg
from .config import TARGETS

CSS = """
:root{--bg:#f6f8fb;--card:#fff;--ink:#14213d;--mut:#5b6b82;--line:#dfe5ee;--navy:#1f3a5f;--teal:#0f8b8d;
--g:#2e7d32;--a:#e0a100;--r:#c62828;--gbg:#e6f4e7;--abg:#fff4d6;--rbg:#fbe4e4}
@media (prefers-color-scheme:dark){:root{--bg:#0f1722;--card:#17212f;--ink:#e8eef7;--mut:#9fb0c6;--line:#2a3a50;--navy:#8fb4e8;--teal:#4cc3c5;
--gbg:#173a1d;--abg:#44370b;--rbg:#4a1b1b;--g:#72c776;--a:#f0c23a;--r:#ff8a80}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:15px/1.5 -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif}
.wrap{max-width:1180px;margin:0 auto;padding:20px 16px 60px}
header{background:var(--navy);color:#fff;padding:22px 16px}header .wrap{padding:0 16px}
header h1{margin:0 0 4px;font-size:24px}header p{margin:0;opacity:.9}
.banner{background:var(--abg);border:1px solid var(--a);padding:8px 12px;border-radius:8px;margin:14px 0;font-size:13px}
h2{margin:30px 0 10px;font-size:19px;color:var(--navy);border-bottom:2px solid var(--line);padding-bottom:5px}
h3{margin:18px 0 6px;font-size:15px}
.card{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:14px 16px;margin:10px 0}
table{border-collapse:collapse;width:100%;font-size:13.5px}th,td{padding:6px 8px;border-bottom:1px solid var(--line);text-align:left;vertical-align:middle}
th{font-size:12px;text-transform:uppercase;letter-spacing:.04em;color:var(--mut)}td.n,th.n{text-align:right;font-variant-numeric:tabular-nums}
.dom td{background:var(--bg);font-weight:700;color:var(--navy)}
.pill{display:inline-block;padding:2px 10px;border-radius:999px;font-size:12px;font-weight:700}
.Green{background:var(--gbg);color:var(--g)}.Amber{background:var(--abg);color:var(--a)}.Red{background:var(--rbg);color:var(--r)}
.High{background:var(--rbg);color:var(--r)}.Medium{background:var(--abg);color:var(--a)}.Low{background:var(--gbg);color:var(--g)}
.grid2{display:grid;grid-template-columns:repeat(auto-fit,minmax(340px,1fr));gap:12px}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:10px}
.kpi{background:var(--card);border:1px solid var(--line);border-radius:10px;padding:10px 12px}.kpi b{display:block;font-size:22px}.kpi span{color:var(--mut);font-size:12px}
.spc{width:100%;height:auto}.spc .ct{font-size:12.5px;font-weight:700;fill:var(--ink)}.spc .ax{font-size:9.5px;fill:var(--mut)}
.spc .grid{stroke:var(--line);stroke-width:.6}.spc .lim{stroke:var(--mut);stroke-dasharray:4 3;fill:none;stroke-width:1}
.spc .cl{stroke:var(--navy);fill:none;stroke-width:1.2}.spc .tgt{stroke:var(--teal);stroke-dasharray:1 3;stroke-width:1.6}
.spc .line{fill:none;stroke:var(--navy);stroke-width:1.5}.spc .pt{fill:var(--navy)}.spc .pt.sig{fill:var(--r)}.spc .base{fill:var(--teal);opacity:.07}
.spark{width:96px;height:26px}.spark .sl{fill:none;stroke:var(--teal);stroke-width:1.5}.spark .sd{fill:var(--teal)}
.f{border-left:4px solid var(--line);padding:2px 0 2px 12px;margin:12px 0}.f.High{border-color:var(--r);background:none;color:inherit}.f.Medium{border-color:var(--a);background:none;color:inherit}
.f h4{margin:0 0 3px;font-size:14.5px}.f p{margin:2px 0;color:var(--mut);font-size:13.5px}.f p b{color:var(--ink)}
details{margin:8px 0}summary{cursor:pointer;font-weight:600;color:var(--navy)}
.heat{text-align:center}.small{font-size:12px;color:var(--mut)}
footer{margin-top:36px;font-size:12px;color:var(--mut)}
@media print{header{-webkit-print-color-adjust:exact;print-color-adjust:exact}.card,.kpi{break-inside:avoid}details{display:block}}
@media (max-width:640px){table{font-size:12.5px}.hide-sm{display:none}}
"""


def esc(x) -> str:
    return html.escape("" if x is None or (isinstance(x, float) and pd.isna(x)) else str(x))


def fmt(v, key=None, nd=1):
    if v is None or pd.isna(v):
        return "–"
    if key == "mortality_oe":
        return f"{v:.2f}"
    return f"{v:,.{nd}f}"


def table(df: pd.DataFrame, num_cols=(), fmts=None, heat=None) -> str:
    fmts = fmts or {}
    h = "".join(f'<th class="{"n" if c in num_cols else ""}">{esc(c.replace("_", " "))}</th>' for c in df.columns)
    rows = []
    for r in df.itertuples(index=False):
        tds = []
        for c, v in zip(df.columns, r):
            txt = fmts[c](v) if c in fmts else esc(v)
            tds.append(f'<td class="{"n" if c in num_cols else ""}">{txt}</td>')
        rows.append("<tr>" + "".join(tds) + "</tr>")
    return f"<table><thead><tr>{h}</tr></thead><tbody>{''.join(rows)}</tbody></table>"


def build(d: dict) -> str:
    sc, s, q = d["scorecard"], d["spc"], d["quarterly"]
    cq = d["current_quarter"]
    qlabel = cq.replace("Q", " Q")
    g = (sc.status == "Green").sum(); a = (sc.status == "Amber").sum(); r = (sc.status == "Red").sum()
    sig_n = d["signals"]["measure_key"].nunique() if len(d["signals"]) else 0
    k = d["volumes"]

    # scorecard
    rows = []
    cur_domain = None
    for x in sc.itertuples():
        if x.domain != cur_domain:
            rows.append(f'<tr class="dom"><td colspan="8">{esc(x.domain)}</td></tr>')
            cur_domain = x.domain
        mser = d["monthly"][d["monthly"].measure_key == x.measure_key].sort_values("month").value.tolist()[-12:]
        arrow = {"improving": "▲ better", "worsening": "▼ worse", "flat": "– flat"}[x.trend]
        arrow_cls = {"improving": "Green", "worsening": "Red", "flat": ""}[x.trend]
        rows.append(
            f'<tr><td>{esc(x.measure)}</td><td class="n"><b>{fmt(x.current, x.measure_key)}</b></td>'
            f'<td class="n">{fmt(x.target, x.measure_key)}</td><td class="n hide-sm">{fmt(x.prior, x.measure_key)}</td>'
            f'<td class="n hide-sm">{fmt(x.year_ago, x.measure_key)}</td>'
            f'<td><span class="small" style="color:var(--{"g" if arrow_cls=="Green" else "r" if arrow_cls=="Red" else "mut"})">{arrow}</span></td>'
            f'<td><span class="pill {x.status}">{x.status}</span></td><td class="hide-sm">{sparkline(mser)}</td></tr>')
    scorecard = ('<table><thead><tr><th>Measure</th><th class="n">' + qlabel + '</th><th class="n">Target</th>'
                 '<th class="n hide-sm">Prior qtr</th><th class="n hide-sm">Year ago</th><th>Trend</th><th>Status</th>'
                 '<th class="hide-sm">Last 12 mo</th></tr></thead><tbody>' + "".join(rows) + "</tbody></table>")

    # findings
    fh = "".join(
        f'<div class="f {esc(f["severity"])}"><h4><span class="pill {esc(f["severity"])}">{esc(f["severity"])}</span> '
        f'{esc(f["title"])} <span class="small">· {esc(f["domain"])}</span></h4>'
        f'<p><b>Evidence:</b> {esc(f["evidence"])}</p><p><b>Suggested action:</b> {esc(f["action"])}</p></div>' for f in d["findings"])

    # spc charts: signalling first
    sig_keys = list(d["signals"].measure_key) if len(d["signals"]) else []
    ordered = sig_keys + [k_ for k_ in TARGETS if k_ not in sig_keys and k_ in set(s.measure_key)]
    def chart(key):
        dd = s[s.measure_key == key]
        nd = 2 if key == "mortality_oe" else 1
        return f'<div class="card">{spc_svg(dd, TARGETS[key]["label"], TARGETS[key]["target"], decimals=nd)}</div>'
    top = "".join(chart(k_) for k_ in ordered[:6])
    rest = "".join(chart(k_) for k_ in ordered[6:])

    # unit drilldown (falls)
    fu = d["fall_units"]
    fp = fu.pivot(index="unit_id", columns="quarter", values="per_1000_pd")
    fp = fp[[c for c in fp.columns if c >= "2025Q1" and c <= cq]]
    fh_rows = []
    vmax = fp.max().max()
    for u, rr in fp.iterrows():
        tds = "".join(f'<td class="heat" style="background:rgba(198,40,40,{min(v / vmax, 1) * .55:.2f})">{v:.1f}</td>' for v in rr)
        fh_rows.append(f"<tr><td><b>{u}</b></td>{tds}</tr>")
    falls_tbl = ("<table><thead><tr><th>Unit</th>" + "".join(f'<th class="heat">{c.replace("Q", " Q")}</th>' for c in fp.columns) +
                 "</tr></thead><tbody>" + "".join(fh_rows) + "</tbody></table>")

    vte = d["vte"].pivot(index="unit_id", columns="admit_day_type", values="value").round(1).reset_index()
    vte_tbl = table(vte, num_cols=("Weekday", "Weekend"), fmts={"Weekday": lambda v: f"{v:.1f}%", "Weekend": lambda v: f"{v:.1f}%"})

    # events
    et = table(d["events_by_type"], num_cols=("events", "serious", "pct_reported_24h"))
    ag = table(d["aging"], num_cols=("events", "high_harm_events")) if len(d["aging"]) else "<p class='small'>No open events.</p>"
    # abstraction
    wl = table(d["workload"], num_cols=("cases_total", "completed", "open_cases", "overdue", "avg_days_to_complete"))
    sub = d["submissions"].copy()
    sub = sub[sub.status != "Not yet due"].sort_values(["quarter", "measure_id"], ascending=[False, True]).head(12)
    sub["due_dt"] = sub.due_dt.str[:10]; sub["submitted_dt"] = sub.submitted_dt.str[:10]
    sub_tbl = table(sub[["measure_id", "quarter", "due_dt", "submitted_dt", "records_submitted", "status"]], num_cols=("records_submitted",))
    irr = table(d["irr"], num_cols=("pairs", "percent_agreement", "kappa"),
                fmts={"percent_agreement": lambda v: f"{v:.1f}%", "kappa": lambda v: f"{v:.2f}"})
    val = table(d["validation"], num_cols=("cases", "agree", "agreement_pct"), fmts={"agreement_pct": lambda v: f"{v:.1f}%"})
    oc = d["open_cases"].head(15).copy()
    oc["selected_dt"] = oc.selected_dt.str[:10]; oc["due_dt"] = oc.due_dt.str[:10]
    oc_tbl = table(oc, num_cols=("days_overdue",))
    oe = d["open_events"].copy(); oe["reported_dt"] = oe.reported_dt.str[:10]
    oe_tbl = table(oe, num_cols=("days_open", "harm_level")) if len(oe) else ""
    dq = table(d["dq"][["rule_id", "table_name", "description", "rows_affected", "action"]], num_cols=("rows_affected",))

    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Quality &amp; Patient Safety Dashboard</title><style>{CSS}</style></head><body>
<header><div class="wrap"><h1>Quality &amp; Patient Safety Dashboard</h1>
<p>{esc(d["hospital"])} · reporting window Nov 2024 – Sep 2026 · data as of {d["as_of"].strftime("%b %d, %Y")} · current quarter {qlabel}</p></div></header>
<div class="wrap">
<div class="kpis">
<div class="kpi"><b>{k["encounters"]:,}</b><span>inpatient encounters</span></div><div class="kpi"><b>{k["ed_visits"]:,}</b><span>ED visits</span></div>
<div class="kpi"><b>{k["events"]:,}</b><span>safety events reported</span></div><div class="kpi"><b>{k["cases"]:,}</b><span>abstraction cases</span></div>
<div class="kpi"><b style="color:var(--g)">{g}</b><span>measures green</span></div><div class="kpi"><b style="color:var(--a)">{a}</b><span>amber</span></div>
<div class="kpi"><b style="color:var(--r)">{r}</b><span>red</span></div><div class="kpi"><b>{sig_n}</b><span>measures with a control-chart signal</span></div></div>

<h2>1. Executive scorecard, {qlabel}</h2><div class="card">{scorecard}</div>
<p class="small">Status: Green meets target; Amber within 10% of target (7% for higher-is-better percentages); Red otherwise. Trend compares with the prior quarter.</p>

<h2>2. What needs the committee's attention</h2><div class="card">{fh}</div>

<h2>3. Control charts</h2>
<p class="small">Centre line and limits are frozen on the first 12 months (shaded). Red points breach a 3-sigma limit, sit in a run of 8 on one side of the centre line, or are part of a run of 6 rising/falling points. Dotted teal line = target.</p>
<div class="grid2">{top}</div><details><summary>Show the other {len(ordered) - 6} control charts</summary><div class="grid2">{rest}</div></details>

<h2>4. Drill-downs</h2>
<div class="grid2"><div class="card"><h3>Falls per 1,000 patient days, by unit and quarter</h3>{falls_tbl}</div>
<div class="card"><h3>VTE prophylaxis (%), by unit and admission day type</h3>{vte_tbl}</div></div>

<h2>5. Safety event management</h2>
<div class="grid2"><div class="card"><h3>Events by type (reporting window)</h3>{et}</div>
<div class="card"><h3>Open events by age (as of extract)</h3>{ag}<h3>Open events</h3>{oe_tbl}</div></div>

<h2>6. Abstraction &amp; public reporting</h2>
<div class="grid2"><div class="card"><h3>Abstractor workload (as of extract)</h3>{wl}<h3>Open cases, oldest due first</h3>{oc_tbl}</div>
<div class="card"><h3>Public-reporting submissions</h3>{sub_tbl}<h3>Inter-rater agreement (second review)</h3>{irr}<h3>Abstracted vs EHR-derived</h3>{val}</div></div>

<h2>7. Data quality &amp; method notes</h2><div class="card">{dq}</div>
<footer><p>Prepared by Naveen Kumar Kovi. Built from SQL views over a cleaned SQLite database. Rate measures use midnight-census patient days and device days; ED medians exclude non-discharged dispositions; mortality O/E uses a simple logistic model fit on the first 12 months. First month (Oct 2024) is excluded as burn-in. See README and docs/ for definitions, limitations and tests.</p></footer>
</div></body></html>"""
