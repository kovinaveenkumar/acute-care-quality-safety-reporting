"""Build every deliverable: HTML dashboard, Excel committee pack, PDF brief, data-quality log CSV."""
from __future__ import annotations

from . import measures as M
from . import report_excel, report_html, report_pdf
from .config import OUT_DIR
from .report_data import collect


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    con = M.connect()
    d = collect(con)
    (OUT_DIR / "dashboard.html").write_text(report_html.build(d), encoding="utf-8")
    report_excel.build(d, OUT_DIR / "Quality_Committee_Pack.xlsx")
    report_pdf.build(d, OUT_DIR / "Quality_Brief.pdf")
    d["scorecard"].to_csv(OUT_DIR / "scorecard_current_quarter.csv", index=False)
    d["spc"].to_csv(OUT_DIR / "spc_monthly.csv", index=False)
    d["dq"].to_csv(OUT_DIR / "data_quality_log.csv", index=False)
    print("built:", ", ".join(p.name for p in sorted(OUT_DIR.iterdir())))


if __name__ == "__main__":
    main()
