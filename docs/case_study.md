# Case study: finding the signal before the committee meeting

**Role:** I worked as the data analyst for a fictional hospital Quality, Risk and Patient Safety team and built the reporting pack end to end.
**Scope:** 24 months, 124-bed community hospital (see Limits for data notes).

## The problem

A quality committee meets monthly. Leaders need to know *what changed, where, and whether it is real*, and they need to trust the numbers. The analyst's job is the chain in between: data access, cleaning, measure logic, charts, drill-downs, safety-event follow-up, abstraction tracking and public-reporting deadlines.

## What I built

A SQL-first pipeline (SQLite) with 10 logged cleaning rules, 18 scorecard measures defined as SQL views, control charts on a frozen baseline, a findings engine, and a web app (QualityLens), and three static formats (HTML dashboard, Excel committee pack, PDF brief). I wrote 30 automated tests that recompute every measure independently and check the pipeline against the defects and signals I injected into the data.

## Lessons, in the order I learned them

**1. Clean data first, and prove the cleaning.** My raw extract had duplicate encounters (30), swapped admit/discharge dates (8), impossible ages (5), missing dispositions (60), duplicate events (25), non-standard unit codes (40), missing report times (15) and events "reported" before they happened (6). My cleaning step logs every rule, and a test confirms the rows flagged equal the defects injected, with none left behind.

**2. Use the right denominator.** Falls and medication events are per 1,000 midnight-census patient days; infections per device day. Counts alone mislead when volume changes. The first month was dropped as burn-in because its patient-day denominators were incomplete.

**3. Control charts beat month-over-month colour changes.** With limits frozen on the first 12 months, deviations stand out instead of being absorbed into the limits. Signals found:

| Signal | What the data showed |
|---|---|
| Falls, one med-surg unit (3 West) | Mar–May 2026: 31 events vs 9.1 expected (12.5 vs 3.7 per 1,000 patient days, 3.4x, Poisson p≈1e-8) |
| VTE prophylaxis, same unit | Weekend admissions: 79.3% vs 92.9% elsewhere (n=725, chi-square p≈1e-38) |
| Sepsis bundle compliance | Fell to 45% in Jan 2026 against a 67% baseline; the weakest element was repeat lactate within 6h (66% vs 86%) |
| Medication events | Jan 2026 at 9.4 per 1,000 patient days vs centre line 4.2 (UCL 7.5) |
| Heart-failure readmissions | 30.2% in Q1 2026 vs a 20% target; back to 22.3% in Q3 |
| ED throughput | Winter surge: boarding peaked at 197 min, discharged-patient LOS at 187 min, LWBS at 4.0% |
| Abstraction backlog | On-time completion fell to 38% for cases selected Feb–Apr 2026 |
| Public reporting | SEP-1 Q4 2025 submitted 3 days after the deadline |

**4. Drill down before you explain.** House-wide falls looked acceptable in some quarters, but the unit table showed one unit running well above its own history. The sepsis dip looked like a general problem until the element-level breakdown showed one step failing. The VTE gap was invisible house-wide (92%) and obvious by unit and weekday.

**5. Small numbers need statistics, not colours.** Infection rates swing wildly on 1–3 events. CLABSI is Red this quarter, yet the Poisson test does not call it a cluster. I made the dashboard say so instead of crying wolf.

**6. Process measures need workflow tracking too.** Quarterly numbers depend on cases being abstracted on time. I added an abstraction tracker, workload table, overdue list, inter-rater agreement (98% agreement, kappa 0.94 on second-reviewed cases) and submission calendar so the reporting itself is auditable.

## How I would explain it to a physician or executive

"Falls on 3 West ran three times their normal rate for three months, and weekend patients on that unit were far less likely to get clot prevention. Both started around the same time and both are fixable processes. Sepsis bundle compliance dipped in January because repeat lactate checks were being missed. Here is the evidence and one suggested action for each."

## Limits

The data is synthetic and I planted the signals in the generator to test my detection, so this shows my method, not real-world discovery. Other limits: simplified measure specs; simple mortality model; no PHI controls or audit trail. See the README for the full list. In a real hospital my first step would be validating each measure's logic against the official specification and the local data.

## Skills demonstrated

SQL (window functions, correlated subqueries, views), Python (pandas, SciPy), statistical process control, hospital quality measures and safety-event workflows, data validation and reconciliation, Excel/PDF/HTML reporting for non-technical audiences, automated testing.
