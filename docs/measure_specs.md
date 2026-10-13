# Measure specifications (simplified)

Reporting window: discharges/events Nov 2024 – Sep 2026 (Oct 2024 excluded as burn-in because patient-day denominators are incomplete). Extract date: 2026-10-13. These specifications are simplified and modelled on public concepts; they are not official.

| Key | Definition | Numerator / denominator | Notes |
|---|---|---|---|
| readmit_30d_rate (+ hf, ami, pn) | Unplanned readmission within 30 days | Index stays with a later non-planned admission of the same patient ≤30 days / eligible index stays | Index: adult, alive at discharge, not OB or behavioral, not AMA/transfer/hospice, full 30-day follow-up available |
| fall_rate, fall_injury_rate | Reported falls per 1,000 patient days | Events / midnight-census patient days | Injury = harm level ≥ 1 |
| med_event_rate | Reported medication events per 1,000 patient days | Events / patient days | |
| clabsi_rate, cauti_rate | Device-associated infections per 1,000 device days | Infections / central-line or catheter days | |
| ed_los_median | Median arrival-to-departure (min) | Discharged ED patients only | Excludes admitted, transferred, LWBS, AMA |
| ed_boarding_median | Median admit decision to ED departure (min) | Admitted ED patients | |
| ed_lwbs_rate | Left without being seen | LWBS visits / all ED visits | |
| sep1_rate | Sepsis bundle compliance | All applicable elements met / non-excluded sepsis cases | Lactate, culture before antibiotics, antibiotics, fluids if hypotensive, repeat lactate if initial >2 |
| ami_asa_rate | Aspirin within 24h of arrival | Given / non-excluded AMI cases | |
| hf_acei_rate | ACEI/ARB/ARNI at discharge for LVSD | Prescribed / non-excluded HF-LVSD discharges | |
| vte_ppx_rate | VTE prophylaxis by end of admission day 1 | Received / non-excluded adult med/surg stays ≥2 days | |
| mortality_oe | Observed / expected inpatient deaths | Deaths / sum of model-expected probabilities | Logistic model on first 12 months; OB excluded |
| event_report_24h | Events reported within 24h of occurrence | Reported ≤24h / events with a reported time | Missing reported_dt excluded |
| event_closed_30d | Events closed within 30 days of report | Closed ≤30d / events reported ≥30 days before extract | Only events old enough to have had the chance |
| abstraction_on_time | Cases completed by due date | Completed ≤ due / cases due on or before extract | Late or still-open overdue cases count as late |

## Control charts

- **p-chart** for proportions, **u-chart** for rates per exposure, **XmR** for medians and O/E.
- Centre line and limits frozen on the first 12 reporting months (Nov 2024 – Oct 2025).
- Signals: point beyond 3 sigma; 8 consecutive points on one side of the centre line; 6 consecutive points rising or falling.

## Scorecard status

Green = meets target. Amber = within 10% of target (7% for higher-is-better percentages). Red = otherwise. Targets are illustrative.
