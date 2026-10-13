"""Committee Excel pack: scorecard with conditional formatting and sparklines, native control charts, trackers."""
from __future__ import annotations

import pandas as pd
import xlsxwriter

from .config import TARGETS

NAVY, TEAL = "#1F3A5F", "#0F8B8D"


def build(d: dict, path) -> None:
    wb = xlsxwriter.Workbook(str(path), {"nan_inf_to_errors": True})
    H = wb.add_format({"bold": True, "font_color": "white", "bg_color": NAVY, "border": 1, "text_wrap": True, "valign": "vcenter"})
    T = wb.add_format({"bold": True, "font_size": 16, "font_color": NAVY})
    S = wb.add_format({"italic": True, "font_color": "#5b6b82"})
    DOM = wb.add_format({"bold": True, "bg_color": "#E8EEF7", "font_color": NAVY})
    B = wb.add_format({"border": 1, "border_color": "#DFE5EE"})
    N1 = wb.add_format({"border": 1, "border_color": "#DFE5EE", "num_format": "#,##0.0"})
    N2 = wb.add_format({"border": 1, "border_color": "#DFE5EE", "num_format": "0.00"})
    N0 = wb.add_format({"border": 1, "border_color": "#DFE5EE", "num_format": "#,##0"})
    WR = wb.add_format({"text_wrap": True, "valign": "top", "border": 1, "border_color": "#DFE5EE"})
    green = wb.add_format({"bg_color": "#E6F4E7", "font_color": "#2E7D32", "bold": True})
    amber = wb.add_format({"bg_color": "#FFF4D6", "font_color": "#8A6D00", "bold": True})
    red = wb.add_format({"bg_color": "#FBE4E4", "font_color": "#C62828", "bold": True})
    cq = d["current_quarter"]

    # ---------------- Scorecard
    ws = wb.add_worksheet("Scorecard")
    ws.write(0, 0, "Quality & Patient Safety Scorecard", T)
    ws.write(1, 0, f"{d['hospital']} | current quarter {cq} | data as of {d['as_of']:%Y-%m-%d}", S)
    hdr = ["Domain", "Measure", f"{cq}", "Target", "Prior qtr", "Year ago", "Change vs prior", "Trend", "Status", "Last 12 months"]
    for c, h in enumerate(hdr):
        ws.write(3, c, h, H)
    monthly = d["monthly"]
    # hidden helper sheet with last-12-month series for sparklines
    hp = wb.add_worksheet("_spark")
    hp.hide()
    r = 4
    for i, x in enumerate(d["scorecard"].itertuples()):
        vals = monthly[monthly.measure_key == x.measure_key].sort_values("month").value.tolist()[-12:]
        for j, v in enumerate(vals):
            hp.write(i, j, v)
        nf = N2 if x.measure_key == "mortality_oe" else N1
        ws.write(r, 0, x.domain, B); ws.write(r, 1, x.measure, B)
        ws.write(r, 2, x.current, nf); ws.write(r, 3, x.target, nf); ws.write(r, 4, x.prior, nf); ws.write(r, 5, x.year_ago, nf)
        ws.write(r, 6, x.delta_vs_prior, nf); ws.write(r, 7, x.trend, B); ws.write(r, 8, x.status, B)
        ws.add_sparkline(r, 9, {"range": f"_spark!A{i + 1}:L{i + 1}", "markers": True, "last_point": True, "series_color": TEAL})
        r += 1
    last = r
    for status, f in (("Green", green), ("Amber", amber), ("Red", red)):
        ws.conditional_format(4, 8, last - 1, 8, {"type": "cell", "criteria": "==", "value": f'"{status}"', "format": f})
    ws.set_column(0, 0, 20); ws.set_column(1, 1, 52); ws.set_column(2, 8, 12); ws.set_column(9, 9, 22)
    ws.freeze_panes(4, 2)
    ws.write(last + 1, 0, "Status: Green meets target; Amber within 10% of target (7% for higher-is-better percentages); Red otherwise.", S)

    # ---------------- Findings
    wf = wb.add_worksheet("Findings")
    for c, h in enumerate(["Severity", "Domain", "Finding", "Evidence", "Suggested action"]):
        wf.write(0, c, h, H)
    for i, f in enumerate(d["findings"], start=1):
        for c, k in enumerate(["severity", "domain", "title", "evidence", "action"]):
            wf.write(i, c, f[k], WR)
    wf.set_column(0, 1, 16); wf.set_column(2, 2, 44); wf.set_column(3, 4, 70)
    wf.conditional_format(1, 0, len(d["findings"]), 0, {"type": "cell", "criteria": "==", "value": '"High"', "format": red})
    wf.conditional_format(1, 0, len(d["findings"]), 0, {"type": "cell", "criteria": "==", "value": '"Medium"', "format": amber})

    # ---------------- SPC data + charts
    wd = wb.add_worksheet("SPC Data")
    cols = ["measure_key", "month", "numerator", "denominator", "value", "center", "ucl", "lcl", "sig_limit", "sig_shift", "sig_trend"]
    for c, h in enumerate(cols):
        wd.write(0, c, h, H)
    spc = d["spc"].sort_values(["measure_key", "month"]).reset_index(drop=True)
    for i, row in enumerate(spc[cols].itertuples(index=False), start=1):
        for c, v in enumerate(row):
            if isinstance(v, (bool,)) or str(type(v)).endswith("bool_'>"):
                wd.write(i, c, "Y" if v else "", B)
            elif isinstance(v, str):
                wd.write(i, c, v)
            elif pd.isna(v):
                wd.write_blank(i, c, None)
            else:
                wd.write(i, c, float(v))
    wd.set_column(0, 0, 22); wd.freeze_panes(1, 0)
    wc = wb.add_worksheet("Control Charts")
    wc.write(0, 0, "Control charts (centre line and 3-sigma limits frozen on first 12 months)", T)
    start = {k: g.index.min() + 2 for k, g in spc.groupby("measure_key")}   # 1-based excel row of first data row
    n = spc.groupby("measure_key").size().to_dict()
    order = list(d["signals"].measure_key) + [k for k in TARGETS if k in n and k not in set(d["signals"].measure_key)]
    for i, key in enumerate(order):
        a, b = start[key], start[key] + n[key] - 1
        ch = wb.add_chart({"type": "line"})
        def ser(col, name, color, dash=None, marker=False, width=1.75):
            line = {"color": color, "width": width}
            if dash: line["dash_type"] = dash
            ch.add_series({"name": name, "categories": f"='SPC Data'!$B${a}:$B${b}", "values": f"='SPC Data'!${col}${a}:${col}${b}",
                           "line": line, "marker": ({"type": "circle", "size": 5, "fill": {"color": color}, "border": {"color": color}} if marker else {"type": "none"})})
        ser("E", "Observed", NAVY, marker=True); ser("F", "Centre line", "#7A8CA5", width=1.25)
        ser("G", "UCL", "#C62828", "dash", width=1); ser("H", "LCL", "#C62828", "dash", width=1)
        ch.set_title({"name": TARGETS[key]["label"], "name_font": {"size": 11}})
        ch.set_legend({"position": "bottom", "font": {"size": 8}})
        ch.set_x_axis({"num_font": {"rotation": -45, "size": 8}, "interval_unit": 2})
        ch.set_y_axis({"major_gridlines": {"visible": True, "line": {"color": "#E5EAF1"}}})
        ch.set_size({"width": 560, "height": 280})
        wc.insert_chart(2 + (i // 2) * 15, (i % 2) * 9, ch)

    # ---------------- Drilldowns
    wu = wb.add_worksheet("Unit Drilldown")
    wu.write(0, 0, "Falls per 1,000 patient days by unit and quarter", T)
    fp = d["fall_units"].pivot(index="unit_id", columns="quarter", values="per_1000_pd")
    fp = fp[[c for c in fp.columns if "2025Q1" <= c <= cq]]
    wu.write(2, 0, "Unit", H)
    for j, c in enumerate(fp.columns, 1):
        wu.write(2, j, c, H)
    for i, (u, rr) in enumerate(fp.iterrows(), start=3):
        wu.write(i, 0, u, B)
        for j, v in enumerate(rr, 1):
            wu.write(i, j, float(v), N1)
    wu.conditional_format(3, 1, 2 + len(fp), len(fp.columns), {"type": "2_color_scale", "min_color": "#FFFFFF", "max_color": "#E57373"})
    r0 = 5 + len(fp)
    wu.write(r0, 0, "VTE prophylaxis % by unit and admission day type", T)
    vt = d["vte"].pivot(index="unit_id", columns="admit_day_type", values="value")
    wu.write(r0 + 1, 0, "Unit", H); wu.write(r0 + 1, 1, "Weekday", H); wu.write(r0 + 1, 2, "Weekend", H)
    for i, (u, rr) in enumerate(vt.iterrows(), start=r0 + 2):
        wu.write(i, 0, u, B); wu.write(i, 1, float(rr["Weekday"]), N1); wu.write(i, 2, float(rr["Weekend"]), N1)
    wu.conditional_format(r0 + 2, 1, r0 + 1 + len(vt), 2, {"type": "3_color_scale", "min_color": "#E57373", "mid_color": "#FFF4D6", "max_color": "#E6F4E7"})
    wu.set_column(0, 12, 12)

    def dump(name, df, widths=None, title=None, numfmt=None):
        w = wb.add_worksheet(name)
        r = 0
        if title:
            w.write(0, 0, title, T); r = 2
        for c, h in enumerate(df.columns):
            w.write(r, c, h, H)
        for i, row in enumerate(df.itertuples(index=False), start=r + 1):
            for c, v in enumerate(row):
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    w.write_blank(i, c, None, B)
                elif isinstance(v, (int, float)) and not isinstance(v, bool):
                    w.write(i, c, v, N1 if isinstance(v, float) else N0)
                else:
                    w.write(i, c, str(v), B)
        w.set_column(0, len(df.columns) - 1, 16)
        if widths:
            for c, wd_ in widths.items():
                w.set_column(c, c, wd_)
        w.freeze_panes(r + 1, 0)
        w.autofilter(r, 0, r + len(df), len(df.columns) - 1)
        return w

    # ---------------- Trackers
    oc = d["open_cases"].copy()
    wt = dump("Abstraction Tracker", oc, title="Open abstraction cases (as of extract date)")
    wt.conditional_format(3, 7, 2 + len(oc), 7, {"type": "cell", "criteria": ">", "value": 0, "format": red})
    dump("Abstractor Workload", d["workload"], title="Abstractor workload")
    sub = d["submissions"].copy()
    ws2 = dump("Public Reporting", sub[["measure_id", "quarter", "due_dt", "submitted_dt", "records_submitted", "accepted", "status", "days_before_due"]],
               title="Public-reporting submissions")
    ws2.conditional_format(3, 6, 2 + len(sub), 6, {"type": "text", "criteria": "containing", "value": "late", "format": amber})
    ws2.conditional_format(3, 6, 2 + len(sub), 6, {"type": "text", "criteria": "containing", "value": "OVERDUE", "format": red})
    dump("Open Safety Events", d["open_events"], title="Safety events not yet closed")
    dump("Events by Type", d["events_by_type"], title="Safety events by type (reporting window)")
    dump("Inter-rater & Validation", pd.concat([d["irr"].assign(table="second-review IRR"),
                                                d["validation"].rename(columns={"cases": "pairs", "agreement_pct": "percent_agreement"}).assign(table="abstracted vs EHR")], ignore_index=True),
         title="Inter-rater agreement and data validation")
    dump("Data Quality Log", d["dq"], title="Cleaning rules applied before reporting", widths={2: 60, 4: 60})

    # ---------------- Definitions
    wdf = wb.add_worksheet("Definitions")
    wdf.write(0, 0, "Measure definitions (simplified; modelled on public quality-measure concepts, not official specifications)", T)
    defs = [
        ("30-day readmission", "Unplanned return to the hospital within 30 days of discharge. Index: adult, alive, not OB/behavioral, not AMA/transfer/hospice, 30 days of follow-up available."),
        ("Falls / medication events", "Reported safety events per 1,000 midnight-census patient days."),
        ("CLABSI / CAUTI", "Device-associated infections per 1,000 central-line / urinary-catheter days."),
        ("ED median LOS", "Median arrival-to-departure in minutes for patients discharged from the ED (excludes admitted, transferred, LWBS, AMA)."),
        ("ED boarding", "Median minutes from admit decision to ED departure for admitted patients."),
        ("SEP-1-style bundle", "All applicable elements met: lactate, blood culture before antibiotics, antibiotics, fluids if hypotensive, repeat lactate if initial lactate > 2."),
        ("AMI aspirin / HF ACEI-ARB-ARNI / VTE prophylaxis", "Numerator / (population minus documented exclusions), by discharge month."),
        ("Mortality O/E", "Observed deaths divided by expected deaths from a logistic model (age, comorbidity, diagnosis group, ICU, ED admit) fit on the first 12 months."),
        ("Control charts", "p-chart (proportions), u-chart (rates per exposure), XmR (medians, O/E). Rules: beyond 3 sigma, 8 in a row on one side, 6 in a row rising/falling."),
    ]
    for i, (k, v) in enumerate(defs, start=2):
        wdf.write(i, 0, k, WR); wdf.write(i, 1, v, WR)
    wdf.set_column(0, 0, 38); wdf.set_column(1, 1, 120)
    wb.close()
