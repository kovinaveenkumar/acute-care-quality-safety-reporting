"""Shared constants: paths, reporting window, units, measure targets."""
from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = ROOT / "data" / "raw"
DB_PATH = ROOT / "data" / "quality.db"
OUT_DIR = ROOT / "outputs"
SQL_DIR = ROOT / "sql"

HOSPITAL = "Lakeshore Community Hospital"
SEED = 20261013

# Reporting window: 24 months of discharges. AS_OF is the date the extract was "pulled".
START = pd.Timestamp("2024-10-01")
END = pd.Timestamp("2026-10-01")  # exclusive
AS_OF = pd.Timestamp("2026-10-13")

UNITS = [
    # unit_id, name, type, beds
    ("ICU", "Intensive Care Unit", "ICU", 12),
    ("TELE", "4 West Telemetry", "Telemetry", 24),
    ("MSE", "3 East Med-Surg", "Med-Surg", 28),
    ("MSW", "3 West Med-Surg", "Med-Surg", 28),
    ("SURG", "5 North Surgical", "Surgical", 20),
    ("OB", "2 East Obstetrics", "Obstetrics", 12),
]

# Illustrative internal targets (NOT national benchmarks). direction: "lower" or "higher" is better.
TARGETS = {
    "readmit_30d_rate": {"label": "30-day all-cause readmission rate (%)", "target": 11.0, "direction": "lower"},
    "readmit_30d_hf": {"label": "30-day readmission, heart failure (%)", "target": 20.0, "direction": "lower"},
    "fall_rate": {"label": "Falls per 1,000 patient days", "target": 3.0, "direction": "lower"},
    "fall_injury_rate": {"label": "Falls with injury per 1,000 patient days", "target": 1.0, "direction": "lower"},
    "med_event_rate": {"label": "Medication events per 1,000 patient days", "target": 4.5, "direction": "lower"},
    "clabsi_rate": {"label": "CLABSI per 1,000 central-line days", "target": 1.0, "direction": "lower"},
    "cauti_rate": {"label": "CAUTI per 1,000 catheter days", "target": 1.3, "direction": "lower"},
    "ed_los_median": {"label": "ED median arrival-to-departure, discharged (min)", "target": 165.0, "direction": "lower"},
    "ed_lwbs_rate": {"label": "ED left without being seen (%)", "target": 2.5, "direction": "lower"},
    "ed_boarding_median": {"label": "ED median admit-decision-to-departure (min)", "target": 150.0, "direction": "lower"},
    "sep1_rate": {"label": "SEP-1-style sepsis bundle compliance (%)", "target": 70.0, "direction": "higher"},
    "ami_asa_rate": {"label": "AMI aspirin within 24h of arrival (%)", "target": 96.0, "direction": "higher"},
    "hf_acei_rate": {"label": "HF with LVSD: ACEI/ARB/ARNI at discharge (%)", "target": 90.0, "direction": "higher"},
    "vte_ppx_rate": {"label": "VTE prophylaxis by end of admission day 1 (%)", "target": 92.0, "direction": "higher"},
    "mortality_oe": {"label": "Inpatient mortality, observed / expected", "target": 1.0, "direction": "lower"},
    "event_report_24h": {"label": "Safety events reported within 24h (%)", "target": 80.0, "direction": "higher"},
    "event_closed_30d": {"label": "Safety events closed within 30 days (%)", "target": 85.0, "direction": "higher"},
    "abstraction_on_time": {"label": "Abstraction cases completed by due date (%)", "target": 95.0, "direction": "higher"},
}

MEASURES_ABSTRACTED = ["SEP1", "AMI_ASA", "HF_ACEI", "VTE_PPX"]
