import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import analysis as an  # noqa: E402


def ts(s):
    return pd.Timestamp(s, tz="UTC")


def make_fc():
    # Target: 2026-01-15 12:00Z.  Forecasts published at various times.
    rows = [
        (ts("2026-01-15 12:00"), ts("2026-01-14 06:00"), 1000.0),  # before gate
        (ts("2026-01-15 12:00"), ts("2026-01-14 08:59"), 1100.0),  # last before 09:00 gate  <- expected
        (ts("2026-01-15 12:00"), ts("2026-01-14 09:30"), 9999.0),  # after gate: must be ignored
        (ts("2026-01-15 12:00"), ts("2026-01-15 11:00"), 1300.0),  # 1h before target
    ]
    return pd.DataFrame(rows, columns=["startTime", "publishTime", "forecast_mw"])


def test_gate_excludes_late_forecasts():
    out = an.latest_at_dayahead_gate(make_fc(), "09:00")
    assert len(out) == 1 and out.forecast_mw.iloc[0] == 1100.0


def test_horizon_selection():
    assert an.latest_at_horizon(make_fc(), 1).forecast_mw.iloc[0] == 1300.0
    # 09:30 on D-1 is 26.5h before target, so it qualifies at a 24h horizon ...
    assert an.latest_at_horizon(make_fc(), 24).forecast_mw.iloc[0] == 9999.0
    # ... but not at 27h, where the 08:59 forecast (27.02h) is the latest eligible one
    assert an.latest_at_horizon(make_fc(), 27).forecast_mw.iloc[0] == 1100.0


def test_error_sign_and_metrics():
    ac = pd.DataFrame({"startTime": [ts("2026-01-15 12:00")], "actual_mw": [1000.0]})
    df = an.pair_with_actuals(an.latest_at_dayahead_gate(make_fc(), "09:00"), ac)
    assert df.error.iloc[0] == 100.0  # over-forecast is positive
    m = an.metrics(df)
    assert m["mae_mw"] == 100.0 and m["bias_mw"] == 100.0 and m["wmape_pct"] == 10.0


def test_planning_band_orders_and_clips():
    hist = pd.DataFrame({"startTime": pd.date_range("2026-01-01", periods=100, freq="30min", tz="UTC"),
                         "error": [-200.0 + 4 * i for i in range(100)]})
    tgt = pd.DataFrame({"startTime": [ts("2026-01-15 12:00")], "forecast_mw": [150.0]})
    b = an.planning_band(hist, tgt, min_per_block=1)
    assert b.p10_mw.iloc[0] <= b.forecast_mw.iloc[0] <= b.p90_mw.iloc[0] + 1e-9 or b.p10_mw.iloc[0] == 0
    assert b.p10_mw.iloc[0] >= 0
