"""Generate a fully synthetic 24-month hospital dataset for a ~124-bed community hospital.

Everything here is invented. Real patterns are modelled loosely (volumes, LOS, readmission
ranges) and a handful of *signals* are deliberately planted so the reporting pipeline has
something to detect. Raw defects (duplicates, typos, swapped dates...) are injected and
counted in data/raw/_defect_manifest.json so the cleaning step can be tested against truth.
"""
from __future__ import annotations

import json
import numpy as np
import pandas as pd

from .config import AS_OF, END, RAW_DIR, SEED, START, UNITS

# ---------------------------------------------------------------- clinical parameters
DX = {
    #        share, LOS median (days), LOS sigma, mortality, readmit, age mean, age sd, ED-admit prob
    "HF":       dict(share=.08, los=4.3, sig=.50, mort=.040, readmit=.21, age=(76, 10), ed=.85,
                     units=dict(TELE=.55, MSE=.20, MSW=.20, ICU=.05)),
    "AMI":      dict(share=.04, los=3.4, sig=.50, mort=.055, readmit=.15, age=(68, 11), ed=.90,
                     units=dict(TELE=.60, ICU=.30, MSE=.05, MSW=.05)),
    "PN":       dict(share=.08, los=4.0, sig=.50, mort=.045, readmit=.16, age=(72, 14), ed=.88,
                     units=dict(MSE=.35, MSW=.35, TELE=.15, ICU=.15)),
    "STROKE":   dict(share=.03, los=4.6, sig=.60, mort=.080, readmit=.11, age=(72, 12), ed=.92,
                     units=dict(TELE=.50, ICU=.30, MSE=.10, MSW=.10)),
    "SEPSIS":   dict(share=.05, los=6.0, sig=.60, mort=.120, readmit=.17, age=(70, 15), ed=.88,
                     units=dict(ICU=.35, MSE=.25, MSW=.25, TELE=.15)),
    "COPD":     dict(share=.05, los=3.6, sig=.45, mort=.020, readmit=.18, age=(70, 10), ed=.90,
                     units=dict(MSE=.40, MSW=.40, TELE=.10, ICU=.10)),
    "OTHER_MED": dict(share=.28, los=3.3, sig=.55, mort=.018, readmit=.11, age=(62, 18), ed=.80,
                      units=dict(MSE=.35, MSW=.35, TELE=.25, ICU=.05)),
    "SURG":     dict(share=.22, los=3.2, sig=.60, mort=.006, readmit=.05, age=(58, 16), ed=.20,
                     units=dict(SURG=.80, ICU=.08, MSE=.06, MSW=.06)),
    "OB":       dict(share=.12, los=2.2, sig=.30, mort=.0003, readmit=.02, age=(29, 5), ed=.35,
                     units=dict(OB=1.0)),
    "BEH":      dict(share=.05, los=6.5, sig=.50, mort=.002, readmit=.14, age=(41, 15), ed=.95,
                     units=dict(MSE=.50, MSW=.50)),
}
PAYERS = ["Medicare", "Medicaid", "Commercial", "Self-pay", "Other"]
PAYER_P = [.42, .27, .21, .06, .04]

EVENT_TYPES = {
    #                    share, harm distribution (levels 0..5)
    "Fall":                  (.20, [.48, .33, .12, .05, .015, .005]),
    "Medication":            (.24, [.70, .18, .08, .025, .0125, .0025]),
    "Pressure Injury":       (.06, [.10, .45, .30, .12, .03, .00]),
    "Surgery/Procedure":     (.07, [.55, .20, .12, .08, .04, .01]),
    "Lab/Specimen":          (.09, [.80, .12, .06, .015, .005, .000]),
    "Equipment/Device":      (.05, [.75, .15, .07, .02, .01, .00]),
    "Behavior/Violence":     (.06, [.50, .30, .15, .04, .01, .00]),
    "Patient ID/Documentation": (.08, [.85, .09, .04, .015, .005, .000]),
    "Diagnosis/Delay":       (.05, [.45, .20, .15, .12, .06, .02]),
    "Other":                 (.10, [.80, .12, .05, .02, .01, .00]),
}
UNIT_EVENT_MULT = {"ICU": 1.3, "TELE": 1.0, "MSE": 1.0, "MSW": 1.0, "SURG": 0.9, "OB": 0.7}
FALL_UNIT_MULT = {"ICU": 0.2, "TELE": 1.1, "MSE": 1.2, "MSW": 1.2, "SURG": 0.8, "OB": 0.1}
ROOT_CAUSES = ["Communication", "Staffing/Workload", "Policy/Process", "Equipment", "Patient factors",
               "EHR/Documentation", "Training", "No contributing factor found"]

HOUR_W = np.array([2, 1.5, 1.2, 1, 1, 1.3, 2, 3, 4.2, 5, 5.5, 5.6, 5.4, 5.2, 5.2, 5.1, 5.0, 5.0, 4.6,
                   4.0, 3.5, 3.0, 2.5, 2.2])
HOUR_W = HOUR_W / HOUR_W.sum()


def _month_bounds(p: pd.Period):
    return p.start_time, (p + 1).start_time


def _winter(m: int) -> float:
    return 1.08 if m in (12, 1, 2) else (1.03 if m in (3, 11) else 1.0)


# ---------------------------------------------------------------- encounters
def gen_encounters(rng: np.random.Generator):
    months = pd.period_range(START, END - pd.Timedelta(days=1), freq="M")
    codes = list(DX)
    shares = np.array([DX[c]["share"] for c in codes])
    shares = shares / shares.sum()
    rows, patients = [], {}
    last_dc: dict[int, pd.Timestamp] = {}
    next_pid = 100000
    next_eid = 5_000_000

    def new_patient(dx, age_mu, age_sd):
        nonlocal next_pid
        age = int(np.clip(rng.normal(age_mu, age_sd), 18, 99)) if dx != "OB" else int(np.clip(rng.normal(29, 5), 16, 46))
        sex = "F" if dx == "OB" else rng.choice(["F", "M"], p=[.52, .48])
        pid = next_pid
        next_pid += 1
        patients[pid] = dict(patient_id=pid, birth_year=2026 - age, sex=sex,
                             payer=rng.choice(PAYERS, p=PAYER_P))
        return pid, age

    pool = []  # patients eligible to be reused
    for p in months:
        m0, m1 = _month_bounds(p)
        n = int(rng.normal(650 * _winter(p.month), 22))
        days = (m1 - m0).days
        for _ in range(n):
            dx = rng.choice(codes, p=shares)
            cfg = DX[dx]
            # admission time (provisional; ED-admits are re-timed below)
            day = int(rng.integers(0, days))
            hour = int(rng.choice(24, p=HOUR_W))
            admit = m0 + pd.Timedelta(days=day, hours=hour, minutes=int(rng.integers(0, 60)))
            if dx == "SURG" and admit.weekday() >= 5 and rng.random() < .7:
                admit = admit - pd.Timedelta(days=admit.weekday() - 4)
            # patient (10% reuse of a patient last discharged >45 days ago)
            pid = None
            if pool and rng.random() < .10:
                cand = pool[int(rng.integers(0, len(pool)))]
                if last_dc.get(cand, pd.Timestamp("2000-01-01")) < admit - pd.Timedelta(days=45) and dx != "OB":
                    pid = cand
            if pid is None:
                pid, age = new_patient(dx, *cfg["age"])
            else:
                age = 2026 - patients[pid]["birth_year"]
            charlson = int(min(8, rng.poisson(max(0.2, (age - 40) / 22) + (1.2 if dx in ("HF", "COPD", "SEPSIS") else 0))))
            u = list(cfg["units"])
            unit = rng.choice(u, p=np.array(list(cfg["units"].values())) / sum(cfg["units"].values()))
            from_ed = rng.random() < cfg["ed"]
            los_days = float(np.exp(rng.normal(np.log(cfg["los"]), cfg["sig"])) * (1 + .06 * charlson))
            los_days = float(np.clip(los_days, .3, 60))
            mort_p = cfg["mort"] * (1 + .25 * charlson) * (1.6 if unit == "ICU" else 1.0)
            # planted: sepsis mortality creeps up Q2 2026 (small)
            died = rng.random() < min(mort_p, .6)
            if died:
                los_days = max(.2, los_days * rng.uniform(.3, 1.0))
            rows.append(dict(
                encounter_id=next_eid, patient_id=pid, dx_group=dx, unit_id=unit, age=age, charlson=charlson,
                admit_dt=admit, los_days=los_days, from_ed=from_ed, died=died, planned_readmit=False,
                index_of=None, payer=patients[pid]["payer"], attending_id=int(rng.integers(1, 41)),
            ))
            eid = next_eid
            next_eid += 1
            dc = admit + pd.Timedelta(days=los_days)
            last_dc[pid] = dc
            pool.append(pid)
            # ---- readmission
            if not died:
                pr = cfg["readmit"] * (1 + .06 * charlson) * (1.0 + (age - 65) / 400)
                if dx == "HF" and pd.Timestamp("2026-01-01") <= admit < pd.Timestamp("2026-04-01"):
                    pr *= 1.35   # planted signal: HF readmission surge Q1 2026
                if rng.random() < min(pr, .6):
                    gap = float(np.clip(rng.exponential(9), .2, 29.5))
                    radmit = dc + pd.Timedelta(days=gap)
                    if radmit < END:
                        rdx = dx if rng.random() < .65 else "OTHER_MED"
                        rcfg = DX[rdx]
                        runit = rng.choice(list(rcfg["units"]), p=np.array(list(rcfg["units"].values())) / sum(rcfg["units"].values()))
                        rlos = float(np.clip(np.exp(rng.normal(np.log(rcfg["los"]), rcfg["sig"])), .3, 40))
                        rdied = rng.random() < min(rcfg["mort"] * 1.5, .5)
                        if rdied:
                            rlos *= rng.uniform(.3, 1.0)
                        rows.append(dict(
                            encounter_id=next_eid, patient_id=pid, dx_group=rdx, unit_id=runit, age=age,
                            charlson=charlson, admit_dt=radmit, los_days=rlos, from_ed=True, died=rdied,
                            planned_readmit=bool(rng.random() < .08), index_of=eid, payer=patients[pid]["payer"],
                            attending_id=int(rng.integers(1, 41))))
                        last_dc[pid] = radmit + pd.Timedelta(days=rlos)
                        next_eid += 1
    enc = pd.DataFrame(rows)
    # keep only admissions inside the reporting window
    enc = enc[(enc.admit_dt >= START) & (enc.admit_dt < END)].copy()
    enc["discharge_dt"] = enc.admit_dt + pd.to_timedelta(enc.los_days, unit="D")
    # discharges after AS_OF would not exist yet; trim by dropping those still "in house"
    enc = enc[enc.discharge_dt <= AS_OF].copy()
    # disposition
    disp = []
    for _, r in enc.iterrows():
        if r.died:
            disp.append("Expired")
        else:
            p_snf = .30 if r.age >= 75 else (.12 if r.age >= 60 else .03)
            p_hh = .12 if r.age >= 65 else .05
            x = rng.random()
            if x < .01: disp.append("Left AMA")
            elif x < .025: disp.append("Transferred")
            elif x < .025 + p_snf: disp.append("SNF")
            elif x < .025 + p_snf + p_hh: disp.append("Home Health")
            elif r.dx_group == "BEH" and x < .6: disp.append("Psych Facility")
            else: disp.append("Home")
    enc["disposition"] = disp
    enc.loc[enc.dx_group.eq("SEPSIS") & rng.random(len(enc)).__lt__(.04) & ~enc.died, "disposition"] = "Hospice"
    return enc.reset_index(drop=True), pd.DataFrame(patients.values())


# ---------------------------------------------------------------- ED
def _ed_los_factor(arr: pd.Series):
    f = np.ones(len(arr))
    f *= np.where(arr.dt.weekday == 0, 1.12, 1.0)
    f *= np.where(arr.dt.hour.between(14, 21), 1.10, 1.0)
    surge = ((arr >= "2025-12-15") & (arr < "2026-03-01")).to_numpy()
    f *= np.where(surge, 1.18, 1.0)
    return f


def gen_ed(enc: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    # ED visits that become admissions
    ea = enc[enc.from_ed].copy()
    n = len(ea)
    board_med = 130 * np.where(((ea.admit_dt >= "2025-12-15") & (ea.admit_dt < "2026-03-01")).to_numpy(), 1.55, 1.0)
    boarding = np.clip(np.exp(rng.normal(np.log(board_med), .75)), 15, 1500)  # minutes
    door_to_decision = np.clip(np.exp(rng.normal(np.log(190), .5)), 30, 900)
    depart = ea.admit_dt.to_numpy()  # ED departure == inpatient arrival
    decision = depart - (boarding * 60e9).astype("timedelta64[ns]")
    arrival = decision - (door_to_decision * 60e9).astype("timedelta64[ns]")
    admit_rows = pd.DataFrame(dict(
        encounter_id=ea.encounter_id.to_numpy(), patient_id=ea.patient_id.to_numpy(), arrival_dt=arrival,
        admit_decision_dt=decision, depart_dt=depart, ed_disposition="Admitted", acuity=rng.choice([1, 2, 3, 4], p=[.05, .35, .5, .10], size=n)))
    # ED treat-and-release visits
    rows = []
    for p in pd.period_range(START, END - pd.Timedelta(days=1), freq="M"):
        m0, m1 = _month_bounds(p)
        k = int(rng.normal(2900 * (1.06 if p.month in (12, 1, 2) else 1.0), 110))
        days = (m1 - m0).days
        arr = m0 + pd.to_timedelta(rng.integers(0, days, k), unit="D") + pd.to_timedelta(rng.choice(24, p=HOUR_W, size=k), unit="h") + pd.to_timedelta(rng.integers(0, 60, k), unit="m")
        rows.append(pd.DataFrame(dict(arrival_dt=arr)))
    ed = pd.concat(rows, ignore_index=True)
    ed = ed[ed.arrival_dt < AS_OF - pd.Timedelta(days=1)]
    lw_p = np.where(((ed.arrival_dt >= "2025-12-01") & (ed.arrival_dt < "2026-03-01")).to_numpy(), .042, .022)
    r = rng.random(len(ed))
    disp = np.select([r < lw_p, r < lw_p + .02, r < lw_p + .03], ["LWBS", "Transferred", "Left AMA"], "Discharged")
    base = 150 * _ed_los_factor(ed.arrival_dt)
    los = np.exp(rng.normal(np.log(base), .6))
    los = np.where(disp == "LWBS", np.exp(rng.normal(np.log(65), .5)), los)
    los = np.clip(los, 10, 1400)
    ed = ed.assign(depart_dt=ed.arrival_dt + pd.to_timedelta(los, unit="m"), ed_disposition=disp,
                   acuity=rng.choice([1, 2, 3, 4, 5], p=[.02, .17, .43, .30, .08], size=len(ed)),
                   encounter_id=np.nan, patient_id=np.nan, admit_decision_dt=pd.NaT)
    allv = pd.concat([admit_rows, ed], ignore_index=True).sort_values("arrival_dt").reset_index(drop=True)
    allv.insert(0, "ed_visit_id", np.arange(9_000_001, 9_000_001 + len(allv)))
    return allv


# ---------------------------------------------------------------- patient days, devices, infections
def patient_days(enc: pd.DataFrame) -> pd.DataFrame:
    """Midnight census: one patient day per midnight an inpatient is in the unit."""
    recs = []
    for r in enc[["unit_id", "admit_dt", "discharge_dt"]].itertuples(index=False):
        d0 = r.admit_dt.normalize() + pd.Timedelta(days=1)
        d1 = r.discharge_dt.normalize()
        if d1 >= d0:
            rng_ = pd.date_range(d0, d1, freq="D")
            recs.append(pd.DataFrame({"unit_id": r.unit_id, "midnight": rng_}))
    pdx = pd.concat(recs, ignore_index=True)
    pdx["month"] = pdx.midnight.dt.to_period("M").astype(str)
    out = pdx.groupby(["unit_id", "month"]).size().rename("patient_days").reset_index()
    # first/last partial months are incomplete by construction; flagged downstream
    return out


def gen_device_days(pdays: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    util_line = {"ICU": .45, "TELE": .08, "MSE": .04, "MSW": .04, "SURG": .07, "OB": .005}
    util_foley = {"ICU": .60, "TELE": .18, "MSE": .14, "MSW": .14, "SURG": .22, "OB": .05}
    d = pdays.copy()
    d["central_line_days"] = [int(max(0, round(p * util_line[u] * rng.normal(1, .06)))) for u, p in zip(d.unit_id, d.patient_days)]
    d["foley_days"] = [int(max(0, round(p * util_foley[u] * rng.normal(1, .06)))) for u, p in zip(d.unit_id, d.patient_days)]
    return d[["unit_id", "month", "central_line_days", "foley_days"]]


def gen_infections(dev: pd.DataFrame, enc: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows, iid = [], 1
    for r in dev.itertuples(index=False):
        for typ, days, base in (("CLABSI", r.central_line_days, 1.0), ("CAUTI", r.foley_days, 1.3)):
            rate = base
            if typ == "CLABSI" and r.unit_id == "ICU" and r.month in ("2026-07", "2026-08"):
                rate = 4.5   # planted cluster
            k = rng.poisson(rate * days / 1000)
            for _ in range(k):
                m0 = pd.Period(r.month).start_time
                span = (pd.Period(r.month) + 1).start_time - m0
                t = m0 + span * rng.random()
                cand = enc[(enc.unit_id == r.unit_id) & (enc.admit_dt <= t) & (enc.discharge_dt >= t)]
                if cand.empty:
                    continue
                e = cand.iloc[int(rng.integers(0, len(cand)))]
                rows.append(dict(infection_id=iid, encounter_id=e.encounter_id, unit_id=r.unit_id, infection_type=typ, onset_dt=t))
                iid += 1
    return pd.DataFrame(rows)


# ---------------------------------------------------------------- safety events
def gen_events(enc: pd.DataFrame, pdays: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    types = list(EVENT_TYPES)
    base_share = np.array([EVENT_TYPES[t][0] for t in types])
    rows, eid = [], 700001
    for r in pdays.itertuples(index=False):
        period = pd.Period(r.month)
        m0, m1 = period.start_time, (period + 1).start_time
        lam_total = 17.0 * r.patient_days / 1000 * UNIT_EVENT_MULT[r.unit_id]
        for ti, typ in enumerate(types):
            lam = lam_total * base_share[ti]
            if typ == "Fall":
                lam *= FALL_UNIT_MULT[r.unit_id]
                if r.unit_id == "MSW" and r.month in ("2026-03", "2026-04", "2026-05"):
                    lam *= 2.4        # planted: fall spike on 3 West
            if typ == "Medication" and r.month in ("2026-01", "2026-02"):
                lam *= 1.9            # planted: medication events after EHR go-live
            if typ == "Pressure Injury" and r.unit_id == "ICU":
                lam *= 2.0
            k = rng.poisson(lam)
            for _ in range(k):
                t = m0 + (m1 - m0) * rng.random()
                harm = int(rng.choice(6, p=np.array(EVENT_TYPES[typ][1]) / sum(EVENT_TYPES[typ][1])))
                # reporting lag
                if rng.random() < (.62 if "2026-01" <= r.month <= "2026-03" else .80):
                    lag = rng.exponential(5) / 24
                else:
                    lag = rng.uniform(1, 12)
                rep = t + pd.Timedelta(days=min(lag, 20))
                if rep > AS_OF:
                    continue
                # review / closure
                med = 9 - (3 if harm >= 3 else 0) + (6 if "2026-02" <= r.month <= "2026-04" else 0)
                rev = rep + pd.Timedelta(days=float(np.clip(rng.gamma(2.2, med / 2.2), .5, 120)))
                status = "Closed" if rev <= AS_OF else ("Under Review" if rep + pd.Timedelta(days=3) < AS_OF else "Open")
                rows.append(dict(event_id=eid, event_dt=t, reported_dt=rep, unit_code=r.unit_id, event_type=typ,
                                 harm_level=harm, status=status,
                                 reviewed_dt=rev if status == "Closed" else pd.NaT,
                                 root_cause=rng.choice(ROOT_CAUSES, p=[.22, .16, .16, .06, .12, .12, .06, .10]) if status == "Closed" else None,
                                 reporter_role=rng.choice(["RN", "Physician", "Pharmacist", "Tech", "Other"], p=[.72, .08, .08, .07, .05])))
                eid += 1
    ev = pd.DataFrame(rows)
    # link to an encounter in that unit at event time (events involving visitors/staff remain unlinked ~7%)
    enc_by_unit = {u: g.sort_values("admit_dt") for u, g in enc.groupby("unit_id")}
    link = []
    for r in ev.itertuples(index=False):
        if rng.random() < .07:
            link.append(np.nan)
            continue
        g = enc_by_unit[r.unit_code]
        c = g[(g.admit_dt <= r.event_dt) & (g.discharge_dt >= r.event_dt)]
        link.append(c.encounter_id.iloc[int(rng.integers(0, len(c)))] if len(c) else np.nan)
    ev["encounter_id"] = link
    return ev


# ---------------------------------------------------------------- chart-abstracted core-measure data
def gen_core_clinical(enc: pd.DataFrame, rng: np.random.Generator) -> pd.DataFrame:
    rows = []
    for r in enc.itertuples(index=False):
        t = r.admit_dt
        # SEP-1-style bundle (sepsis admissions)
        if r.dx_group == "SEPSIS":
            excl = r.disposition == "Hospice" or rng.random() < .03
            q1 = pd.Timestamp("2026-01-05") <= t < pd.Timestamp("2026-04-01")
            hypo = rng.random() < .45
            hi_lac = rng.random() < .60
            e = dict(
                lactate=rng.random() < .93, cx=rng.random() < .90, abx=rng.random() < .92,
                fluids=(not hypo) or rng.random() < .88,
                repeat_lac=(not hi_lac) or rng.random() < (.55 if q1 else .85))
            rows.append(dict(encounter_id=r.encounter_id, measure_id="SEP1", excluded=excl,
                             numerator=all(e.values()), detail=json.dumps({**e, "hypotension": hypo, "initial_lactate_gt2": hi_lac})))
        # AMI aspirin on arrival
        if r.dx_group == "AMI":
            excl = r.disposition in ("Transferred",) or rng.random() < .03
            rows.append(dict(encounter_id=r.encounter_id, measure_id="AMI_ASA", excluded=excl,
                             numerator=rng.random() < .965, detail="{}"))
        # HF LVSD: ACEI/ARB/ARNI at discharge
        if r.dx_group == "HF" and not r.died and rng.random() < .45:
            months_in = (t.year - 2024) * 12 + t.month - 10
            p = .84 + .0045 * months_in
            excl = r.disposition in ("Transferred", "Left AMA", "Hospice") or rng.random() < .12
            rows.append(dict(encounter_id=r.encounter_id, measure_id="HF_ACEI", excluded=excl,
                             numerator=rng.random() < min(p, .96), detail="{}"))
        # VTE prophylaxis (adult med/surg, LOS >= 2 d)
        if r.dx_group not in ("OB", "BEH") and r.los_days >= 2 and not r.died:
            excl = rng.random() < .10
            p = .93
            if r.unit_id == "MSW" and t.weekday() >= 5:
                p = .78  # planted: weekend admissions to 3 West miss prophylaxis
            rows.append(dict(encounter_id=r.encounter_id, measure_id="VTE_PPX", excluded=excl,
                             numerator=rng.random() < p, detail="{}"))
    return pd.DataFrame(rows)


def gen_abstraction(enc: pd.DataFrame, clin: pd.DataFrame, rng: np.random.Generator):
    abstractors = ["A. Rivera", "B. Okafor", "C. Nguyen", "D. Patel"]
    ew = [.30, .30, .25, .15]
    quotas = {"SEP1": 25, "AMI_ASA": 15, "HF_ACEI": 20, "VTE_PPX": 25}
    c = clin[~clin.excluded].merge(enc[["encounter_id", "discharge_dt"]], on="encounter_id")
    c["month"] = c.discharge_dt.dt.to_period("M")
    rows, cid = [], 1
    for (meas, mon), g in c.groupby(["measure_id", "month"]):
        k = min(len(g), quotas[meas])
        pick = g.sample(k, random_state=int(rng.integers(0, 1_000_000)))
        selected = (mon + 1).start_time + pd.Timedelta(days=9)   # sample drawn the 10th after month close
        if selected > AS_OF:
            continue
        for r in pick.itertuples(index=False):
            due = selected + pd.Timedelta(days=21)
            backlog = pd.Timestamp("2026-02-01") <= selected < pd.Timestamp("2026-05-01")
            lag = rng.gamma(4, 3.2 if not backlog else 6.2)
            comp = selected + pd.Timedelta(days=float(lag))
            if comp > AS_OF:
                status = "In Progress" if rng.random() < .55 else "Not Started"
                comp, abs_num = pd.NaT, None
            else:
                status = "Completed"
                abs_num = (not r.numerator) if rng.random() < .04 else r.numerator
            a = rng.choice(abstractors, p=ew)
            second = status == "Completed" and rng.random() < .12
            second_num = None
            if second:
                second_num = (not abs_num) if rng.random() < .03 else abs_num
            rows.append(dict(case_id=cid, measure_id=meas, encounter_id=r.encounter_id, selected_dt=selected,
                             due_dt=due, abstractor=a, status=status, completed_dt=comp,
                             abstracted_numerator=abs_num, second_review=second, second_numerator=second_num))
            cid += 1
    cases = pd.DataFrame(rows)

    subs = []
    for meas in quotas:
        for q in pd.period_range("2024Q4", "2026Q3", freq="Q"):
            due = q.end_time.normalize() + pd.Timedelta(days=120)
            n = int(cases[(cases.measure_id == meas) & (pd.to_datetime(cases.selected_dt) >= q.start_time + pd.Timedelta(days=0))
                          & (pd.to_datetime(cases.selected_dt) < (q + 1).start_time + pd.Timedelta(days=15))
                          & (cases.status == "Completed")].shape[0])
            sub = due - pd.Timedelta(days=int(rng.integers(2, 20)))
            if meas == "SEP1" and str(q) == "2025Q4":
                sub = due + pd.Timedelta(days=3)    # planted late submission
            if sub > AS_OF:
                sub = pd.NaT
            subs.append(dict(measure_id=meas, quarter=str(q), due_dt=due, submitted_dt=sub, records_submitted=n if pd.notna(sub) else None,
                             accepted=(rng.random() < .985) if pd.notna(sub) else None))
    return cases, pd.DataFrame(subs)


# ---------------------------------------------------------------- inject raw defects
def inject_defects(enc, ev, rng):
    """Inject raw-data defects into DISJOINT row sets so the manifest counts are exact."""
    m = {}
    enc = enc.reset_index(drop=True).copy()
    ev = ev.reset_index(drop=True).copy()
    # ---- encounters
    order = enc.sample(frac=1, random_state=11).index.to_list()
    sw, mis, age_o, dup_i = order[:8], order[8:68], order[68:73], order[73:103]
    enc.loc[sw, ["admit_dt", "discharge_dt"]] = enc.loc[sw, ["discharge_dt", "admit_dt"]].to_numpy()
    enc.loc[mis, "disposition"] = None
    enc.loc[age_o, "age"] = 150
    m["encounter_dates_swapped"] = len(sw)
    m["encounter_missing_disposition"] = len(mis)
    m["encounter_age_outlier"] = len(age_o)
    enc = pd.concat([enc, enc.loc[dup_i]], ignore_index=True)
    m["encounter_duplicate_rows"] = len(dup_i)
    # ---- events
    order = ev.sample(frac=1, random_state=12).index.to_list()
    mi, ty, rb, dd = order[:15], order[15:55], order[55:61], order[61:86]
    ev.loc[mi, "reported_dt"] = pd.NaT
    mp = {"MSW": ["3west", "3 WEST", "msw "], "MSE": ["3east", "mse "], "ICU": ["icu", "ICU "], "TELE": ["tele", "4W"], "SURG": ["surg"], "OB": ["ob"]}
    ev.loc[ty, "unit_code"] = [rng.choice(mp[u]) for u in ev.loc[ty, "unit_code"]]
    ev.loc[rb, "reported_dt"] = ev.loc[rb, "event_dt"] - pd.Timedelta(days=2)
    m["event_missing_reported_dt"] = len(mi)
    m["event_unit_code_typo"] = len(ty)
    m["event_reported_before_event"] = len(rb)
    ev = pd.concat([ev, ev.loc[dd]], ignore_index=True)
    m["event_duplicate_rows"] = len(dd)
    return enc, ev, m


def main():
    rng = np.random.default_rng(SEED)
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    enc, patients = gen_encounters(rng)
    ed = gen_ed(enc, rng)
    pdays = patient_days(enc)
    dev = gen_device_days(pdays, rng)
    inf = gen_infections(dev, enc, rng)
    ev = gen_events(enc, pdays, rng)
    clin = gen_core_clinical(enc, rng)
    cases, subs = gen_abstraction(enc, clin, rng)

    enc_out = enc.drop(columns=["los_days"]).rename(columns={"died": "died_flag"})
    enc_out["died_flag"] = enc_out.died_flag.astype(int)
    enc_out["planned_readmit"] = enc_out.planned_readmit.astype(int)
    enc_out["from_ed"] = enc_out.from_ed.astype(int)
    enc_out, ev_out, manifest = inject_defects(enc_out, ev, rng)

    units = pd.DataFrame(UNITS, columns=["unit_id", "unit_name", "unit_type", "beds"])
    providers = pd.DataFrame({"provider_id": range(1, 41),
                              "provider_name": [f"Provider {i:02d}" for i in range(1, 41)],
                              "specialty": np.random.default_rng(1).choice(["Hospitalist", "Cardiology", "Pulmonology", "Surgery", "OB/GYN", "Neurology", "Psychiatry"], 40)})
    files = {"units": units, "providers": providers, "patients": patients, "encounters": enc_out, "ed_visits": ed,
             "patient_days": pdays, "device_days": dev, "infections": inf, "safety_events": ev_out,
             "core_measure_clinical": clin, "abstraction_cases": cases, "public_reporting_submissions": subs}
    for name, df in files.items():
        df.to_csv(RAW_DIR / f"{name}.csv", index=False)
        print(f"{name:32s} {len(df):>8,d} rows")
    manifest["generated_for_seed"] = SEED
    (RAW_DIR / "_defect_manifest.json").write_text(json.dumps(manifest, indent=2))
    print("defects injected:", manifest)


if __name__ == "__main__":
    main()
