import numpy as np
import pandas as pd
import pytest

from qsr.measures import cohen_kappa, rag
from qsr.spc import control_chart


def _df(vals, den=100):
    m = [str(p) for p in pd.period_range("2024-11", periods=len(vals), freq="M")]
    return pd.DataFrame({"month": m, "numerator": [v * den / 100 for v in vals], "denominator": den, "value": vals})


def test_p_chart_limits_known_values():
    d = control_chart(_df([10.0] * 12 + [10.0] * 3), "p", 100)
    p, n = .10, 100
    expected_ucl = (p + 3 * np.sqrt(p * (1 - p) / n)) * 100
    assert d.center.iloc[0] == pytest.approx(10.0)
    assert d.ucl.iloc[0] == pytest.approx(expected_ucl)
    assert d.lcl.iloc[0] == pytest.approx(10 - (expected_ucl - 10))
    assert not d.any_signal.any()


def test_limit_breach_detected():
    d = control_chart(_df([10, 11, 9, 10, 12, 8, 10, 11, 9, 10, 11, 9] + [30]), "p", 100)
    assert bool(d.sig_limit.iloc[-1]) and not d.sig_limit.iloc[:12].any()


def test_shift_rule_needs_eight_in_a_row():
    base = [10, 12, 8, 11, 9, 10, 12, 8, 11, 9, 10, 10]
    seven = control_chart(_df(base + [11] * 7), "p", 100)
    eight = control_chart(_df(base + [11] * 8), "p", 100)
    assert not seven.sig_shift.iloc[12:].any()
    assert eight.sig_shift.iloc[12:].all()


def test_trend_rule():
    base = [10, 12, 8, 11, 9, 10, 12, 8, 11, 9, 10, 10]
    d = control_chart(_df(base + [10.5, 11, 11.5, 12, 12.5, 13]), "p", 100)
    assert d.sig_trend.iloc[-6:].all()


def test_u_chart_center_is_pooled_rate():
    m = [str(p) for p in pd.period_range("2024-11", periods=14, freq="M")]
    df = pd.DataFrame({"month": m, "numerator": [3] * 14, "denominator": [1000] * 14, "value": [3.0] * 14})
    d = control_chart(df, "u", 1000)
    assert d.center.iloc[0] == pytest.approx(3.0)
    assert (d.lcl >= 0).all()


def test_xmr_limits():
    vals = [100, 102, 98, 101, 99, 100, 103, 97, 100, 101, 99, 100, 150]
    m = [str(p) for p in pd.period_range("2024-11", periods=len(vals), freq="M")]
    d = control_chart(pd.DataFrame({"month": m, "numerator": np.nan, "denominator": np.nan, "value": vals}), "i", 1)
    mr = np.abs(np.diff(vals[:12])).mean()
    assert d.ucl.iloc[0] == pytest.approx(np.mean(vals[:12]) + 2.66 * mr)
    assert bool(d.sig_limit.iloc[-1])


def test_cohen_kappa():
    assert cohen_kappa(np.array([1, 1, 0, 0]), np.array([1, 1, 0, 0])) == pytest.approx(1.0)
    assert cohen_kappa(np.array([1, 0, 1, 0]), np.array([0, 1, 0, 1])) == pytest.approx(-1.0)
    # 90 agree of 100 with balanced marginals -> kappa 0.8
    a = np.array([1] * 50 + [0] * 50)
    b = a.copy(); b[:5] = 0; b[50:55] = 1
    assert cohen_kappa(a, b) == pytest.approx(0.8)


@pytest.mark.parametrize("key,value,expected", [
    ("fall_rate", 3.0, "Green"), ("fall_rate", 3.29, "Amber"), ("fall_rate", 3.5, "Red"),
    ("sep1_rate", 70, "Green"), ("sep1_rate", 66, "Amber"), ("sep1_rate", 60, "Red"),
])
def test_rag_boundaries(key, value, expected):
    assert rag(value, key) == expected
