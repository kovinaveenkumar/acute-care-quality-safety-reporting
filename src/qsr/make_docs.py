"""Generate docs/data_dictionary.md from the live SQLite schema so it can never drift from the code."""
from __future__ import annotations

import sqlite3

from .config import DB_PATH, ROOT

DESC = {
    "encounter": "One inpatient stay (index and readmission stays). Cleaned: duplicates dropped, swapped dates fixed.",
    "ed_visit": "One ED visit. Admitted visits link to an encounter; treat-and-release visits do not.",
    "safety_event": "Voluntarily reported patient-safety event (fall, medication, etc.) with harm level 0-5 and review status.",
    "infection": "Device-associated infection (CLABSI / CAUTI) linked to an encounter and unit.",
    "patient_days": "Midnight-census patient days per unit and month (denominator for event rates).",
    "device_days": "Central-line and urinary-catheter days per unit and month (denominator for infection rates).",
    "core_measure_clinical": "EHR-derived measure population: exclusion flag and numerator flag per encounter and measure.",
    "abstraction_case": "Sampled case sent to a quality abstractor: due date, status, abstracted result, optional second review.",
    "public_reporting_submission": "Quarterly submission log per measure with due and submitted dates.",
    "mortality_expected": "Expected probability of death per encounter from the logistic baseline model.",
    "dq_log": "Every cleaning rule applied, with the number of rows affected.",
    "meta": "Extract date and other run metadata.",
    "unit": "Nursing units and bed counts.", "patient": "Synthetic patient demographics.",
}


def main():
    con = sqlite3.connect(DB_PATH)
    lines = ["# Data dictionary", "", "Generated from the live schema by `python -m qsr.make_docs`. All data is synthetic.", ""]
    tables = [r[0] for r in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")]
    for t in tables:
        n = con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        lines += [f"## `{t}` ({n:,} rows)", "", DESC.get(t, ""), "", "| column | type | key |", "|---|---|---|"]
        for _, name, typ, notnull, _, pk in con.execute(f"PRAGMA table_info({t})"):
            lines.append(f"| {name} | {typ or ''} | {'PK' if pk else ''} |")
        lines.append("")
    lines += ["## Measure views", ""]
    for (v,) in con.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name"):
        lines.append(f"- `{v}`")
    (ROOT / "docs" / "data_dictionary.md").write_text("\n".join(lines) + "\n")
    print("wrote docs/data_dictionary.md")


if __name__ == "__main__":
    main()
