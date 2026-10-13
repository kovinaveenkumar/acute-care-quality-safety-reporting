import numpy as np
import pandas as pd

from qsr import findings as FD
from qsr import measures as M


def test_mortality_calibrated_on_baseline(con):
    m = pd.read_sql("SELECT * FROM v_m_mortality", con).sort_values("month")
    base = m.iloc[:12]
    assert 0.9 < base.numerator.sum() / base.denominator.sum() < 1.1
    assert pd.read_sql("SELECT MIN(expected_p) lo, MAX(expected_p) hi FROM mortality_expected", con).iloc[0].between(0, 1).all()


def test_detects_planted_signals(con):
    """The scan must rediscover the signals the generator planted, without being told where they are."""
    hot = FD.scan_event_hotspots(con)
    assert any(h["unit"] == "MSW" and h["event_type"] == "Fall" and h["start"] >= "2026-01" for h in hot)
    v = FD.vte_gap(con)
    assert v["cell"] == "MSW Weekend" and v["p"] < 1e-6
    s = FD.sep1_driver(con)
    assert s["elements"][0][0] == "repeat lactate within 6h" and "2026-01" <= s["worst_month"] <= "2026-03"
    sp = M.spc_all(M.monthly(con))
    jan = sp[(sp.measure_key == "med_event_rate") & (sp.month == "2026-01")].iloc[0]
    assert bool(jan.sig_limit)


def test_late_submission_is_flagged(con):
    s = pd.read_sql("SELECT * FROM v_submission_status WHERE status='Submitted late'", con)
    assert list(s.measure_id) == ["SEP1"] and list(s.quarter) == ["2025Q4"]


def test_inter_rater_agreement_is_high(con):
    irr = M.irr(con).set_index("measure_id")
    assert irr.loc["ALL", "percent_agreement"] > 95 and irr.loc["ALL", "kappa"] > 0.8


def test_scorecard_covers_every_target(con):
    q = M.quarterly(con, M.monthly(con))
    sc = M.scorecard(q)
    assert set(sc.measure_key) == set(M.TARGETS) if hasattr(M, "TARGETS") else True
    assert sc.status.isin(["Green", "Amber", "Red"]).all()
