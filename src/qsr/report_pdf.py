"""Board/committee PDF brief built with matplotlib (no external tools needed)."""
from __future__ import annotations

import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages

from .config import TARGETS

NAVY, TEAL, RED, GREEN, AMBER = "#1F3A5F", "#0F8B8D", "#C62828", "#2E7D32", "#E0A100"
STAT = {"Green": "#E6F4E7", "Amber": "#FFF4D6", "Red": "#FBE4E4"}


def _header(fig, title, sub):
    fig.text(.06, .955, title, fontsize=17, weight="bold", color=NAVY)
    fig.text(.06, .93, sub, fontsize=8.5, color="#5b6b82")


def build(d: dict, path) -> None:
    cq = d["current_quarter"].replace("Q", " Q")
    sub = f"{d['hospital']} | data as of {d['as_of']:%b %d, %Y} "
    with PdfPages(path) as pdf:
        # ---- page 1 scorecard
        fig = plt.figure(figsize=(8.5, 11))
        _header(fig, f"Quality & Patient Safety Brief, {cq}", sub)
        sc = d["scorecard"]
        ax = fig.add_axes([.05, .06, .9, .84]); ax.axis("off")
        rows = [[r.measure, f"{r.current:.2f}" if r.measure_key == "mortality_oe" else f"{r.current:.1f}",
                 f"{r.target:g}", {"improving": "better", "worsening": "worse", "flat": "flat"}[r.trend], r.status] for r in sc.itertuples()]
        t = ax.table(cellText=rows, colLabels=[f"Measure", cq, "Target", "vs prior", "Status"], colWidths=[.58, .1, .1, .11, .11],
                     loc="upper center", cellLoc="left")
        t.auto_set_font_size(False); t.set_fontsize(8); t.scale(1, 1.55)
        for (i, j), c in t.get_celld().items():
            c.set_edgecolor("#DFE5EE")
            if i == 0:
                c.set_facecolor(NAVY); c.get_text().set_color("white"); c.get_text().set_weight("bold")
            elif j == 4:
                c.set_facecolor(STAT[rows[i - 1][4]]); c.get_text().set_weight("bold")
            if j in (1, 2, 3) and i > 0:
                c.get_text().set_ha("center")
        pdf.savefig(fig); plt.close(fig)

        # ---- page 2 findings
        fig = plt.figure(figsize=(8.5, 11))
        _header(fig, "What needs attention", sub)
        y = .90
        for f in d["findings"]:
            ev = textwrap.fill(f["evidence"], 105); ac = textwrap.fill("Suggested action: " + f["action"], 105)
            lines = 1 + ev.count("\n") + 1 + ac.count("\n") + 1
            need = .0145 * (lines + 1.2)
            if y - need < .04:
                pdf.savefig(fig); plt.close(fig)
                fig = plt.figure(figsize=(8.5, 11)); _header(fig, "What needs attention (cont.)", sub); y = .90
            col = RED if f["severity"] == "High" else AMBER
            fig.patches.append(plt.Rectangle((.06, y - need + .005), .006, need - .004, transform=fig.transFigure, color=col))
            fig.text(.08, y - .012, f"[{f['severity']}] {f['title']}", fontsize=9.5, weight="bold", color=NAVY, va="top")
            fig.text(.08, y - .028, ev, fontsize=8, va="top", color="#222")
            fig.text(.08, y - .028 - .0145 * (ev.count("\n") + 1.3), ac, fontsize=8, va="top", color="#5b6b82", style="italic")
            y -= need + .012
        pdf.savefig(fig); plt.close(fig)

        # ---- control chart pages
        s = d["spc"]
        sig = list(d["signals"].measure_key)
        keys = sig + [k for k in TARGETS if k not in sig and k in set(s.measure_key)]
        for p in range(0, len(keys), 6):
            fig, axes = plt.subplots(3, 2, figsize=(8.5, 11)); fig.subplots_adjust(top=.9, hspace=.5, wspace=.25, left=.08, right=.97, bottom=.05)
            _header(fig, "Control charts", "Baseline = first 12 months (shaded). Red = signal. Dotted = target.")
            for ax, k in zip(axes.flat, keys[p:p + 6]):
                g = s[s.measure_key == k].sort_values("month")
                x = range(len(g))
                ax.axvspan(0, 11, color=TEAL, alpha=.07)
                ax.plot(x, g.ucl, "--", color="#8a97ab", lw=.9); ax.plot(x, g.lcl, "--", color="#8a97ab", lw=.9)
                ax.plot(x, g.center, color=NAVY, lw=1)
                ax.axhline(TARGETS[k]["target"], color=TEAL, ls=":", lw=1.4)
                ax.plot(x, g.value, "-o", color=NAVY, ms=3, lw=1.3)
                sg = g[g.any_signal]
                ax.plot([list(g.month).index(m) for m in sg.month], sg.value, "o", color=RED, ms=5)
                ax.set_title(TARGETS[k]["label"], fontsize=8, loc="left", color=NAVY, weight="bold")
                ax.set_xticks(list(x)[::4]); ax.set_xticklabels([m[2:] for m in g.month][::4], fontsize=6.5)
                ax.tick_params(axis="y", labelsize=6.5)
                for sp in ("top", "right"):
                    ax.spines[sp].set_visible(False)
            for ax in list(axes.flat)[len(keys[p:p + 6]):]:
                ax.axis("off")
            pdf.savefig(fig); plt.close(fig)

        # ---- abstraction page
        fig = plt.figure(figsize=(8.5, 11)); _header(fig, "Abstraction & public reporting", sub)
        ax = fig.add_axes([.06, .55, .88, .33]); ax.axis("off")
        wl = d["workload"]
        ax.set_title("Abstractor workload (as of extract date)", loc="left", fontsize=10, color=NAVY, weight="bold")
        t = ax.table(cellText=wl.round(1).astype(str).values.tolist(), colLabels=list(wl.columns), loc="upper center")
        t.auto_set_font_size(False); t.set_fontsize(8); t.scale(1, 1.5)
        ax2 = fig.add_axes([.06, .08, .88, .38]); ax2.axis("off")
        sub_df = d["submissions"]; sub_df = sub_df[sub_df.status != "Not yet due"].sort_values(["quarter", "measure_id"], ascending=[False, True]).head(10)
        ax2.set_title("Public-reporting submissions (most recent due)", loc="left", fontsize=10, color=NAVY, weight="bold")
        cells = [[r.measure_id, r.quarter, str(r.due_dt)[:10], str(r.submitted_dt)[:10], r.status] for r in sub_df.itertuples()]
        t2 = ax2.table(cellText=cells, colLabels=["Measure", "Quarter", "Due", "Submitted", "Status"], loc="upper center")
        t2.auto_set_font_size(False); t2.set_fontsize(8); t2.scale(1, 1.5)
        pdf.savefig(fig); plt.close(fig)
