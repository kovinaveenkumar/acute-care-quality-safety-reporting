"""Tiny dependency-free SVG chart helpers for the HTML dashboard."""
from __future__ import annotations

import html
import pandas as pd

MONTHS = "Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec".split()


def month_label(m: str) -> str:
    y, mo = m.split("-")
    return f"{MONTHS[int(mo) - 1]} {y[2:]}"


def spc_svg(d: pd.DataFrame, title: str, target: float | None = None, w=560, h=210, decimals=1) -> str:
    d = d.reset_index(drop=True)
    pad_l, pad_r, pad_t, pad_b = 46, 10, 26, 28
    vals = list(d.value) + list(d.ucl) + list(d.lcl) + ([target] if target is not None else [])
    lo, hi = min(vals), max(vals)
    span = (hi - lo) or 1
    lo, hi = lo - span * .06, hi + span * .06
    X = lambda i: pad_l + i * (w - pad_l - pad_r) / max(len(d) - 1, 1)
    Y = lambda v: pad_t + (hi - v) * (h - pad_t - pad_b) / (hi - lo)
    parts = [f'<svg viewBox="0 0 {w} {h}" role="img" aria-label="{html.escape(title)}" class="spc">',
             f'<text x="{pad_l}" y="15" class="ct">{html.escape(title)}</text>']
    for t in (lo + (hi - lo) * k / 3 for k in range(4)):
        parts.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{Y(t):.1f}" y2="{Y(t):.1f}" class="grid"/>'
                     f'<text x="{pad_l - 5}" y="{Y(t) + 3:.1f}" class="ax" text-anchor="end">{t:.{decimals}f}</text>')
    for i, m in enumerate(d.month):
        if i % 3 == 0:
            parts.append(f'<text x="{X(i):.1f}" y="{h - 10}" class="ax" text-anchor="middle">{month_label(m)}</text>')
    # limits as step polylines (p/u charts have varying limits)
    for col, cls in (("ucl", "lim"), ("lcl", "lim"), ("center", "cl")):
        pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(d[col]))
        parts.append(f'<polyline points="{pts}" class="{cls}"/>')
    if target is not None:
        parts.append(f'<line x1="{pad_l}" x2="{w - pad_r}" y1="{Y(target):.1f}" y2="{Y(target):.1f}" class="tgt"/>')
    # baseline shading (first 12 points)
    bx = X(min(11, len(d) - 1))
    parts.append(f'<rect x="{pad_l}" y="{pad_t}" width="{bx - pad_l:.1f}" height="{h - pad_t - pad_b}" class="base"/>')
    pts = " ".join(f"{X(i):.1f},{Y(v):.1f}" for i, v in enumerate(d.value))
    parts.append(f'<polyline points="{pts}" class="line"/>')
    for i, r in d.iterrows():
        cls = "pt sig" if r.any_signal else "pt"
        parts.append(f'<circle cx="{X(i):.1f}" cy="{Y(r.value):.1f}" r="{3.4 if r.any_signal else 2.6}" class="{cls}">'
                     f'<title>{month_label(r.month)}: {r.value:.{decimals}f}</title></circle>')
    parts.append("</svg>")
    return "".join(parts)


def sparkline(values, w=96, h=26) -> str:
    v = [x for x in values if pd.notna(x)]
    if len(v) < 2:
        return ""
    lo, hi = min(v), max(v)
    span = (hi - lo) or 1
    pts = " ".join(f"{2 + i * (w - 4) / (len(v) - 1):.1f},{h - 3 - (x - lo) * (h - 6) / span:.1f}" for i, x in enumerate(v))
    last = pts.split()[-1].split(",")
    return (f'<svg viewBox="0 0 {w} {h}" class="spark" aria-hidden="true"><polyline points="{pts}" class="sl"/>'
            f'<circle cx="{last[0]}" cy="{last[1]}" r="2.4" class="sd"/></svg>')
