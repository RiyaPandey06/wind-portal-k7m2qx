"""Pure-pandas analysis. No I/O here, so it is trivially unit-testable.

Conventions
-----------
* error = forecast - actual  (MW).  error > 0  => wind OVER-forecast => the buyer
  procured too little thermal/other power and is short in real time (the costly side).
* "Delivery day" D is a London-local calendar day; the day-ahead decision for D is
  taken on D-1 and may only use forecasts published before the gate cutoff on D-1.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

LONDON = "Europe/London"
HALF_HOUR_H = 0.5


def _parse_cutoff(cutoff: str) -> pd.Timedelta:
    h, m = (int(x) for x in cutoff.split(":"))
    return pd.Timedelta(hours=h, minutes=m)


def delivery_day(ts: pd.Series) -> pd.Series:
    """London-local calendar date of each timestamp (as tz-naive midnight)."""
    return ts.dt.tz_convert(LONDON).dt.tz_localize(None).dt.normalize()


def latest_at_dayahead_gate(fc: pd.DataFrame, cutoff: str = "09:00") -> pd.DataFrame:
    """For each target half-hour: the most recent forecast published at/before the
    gate on D-1 (London time). Returns one row per startTime."""
    if fc.empty:
        return fc.assign(horizon_h=pd.Series(dtype=float))
    day = delivery_day(fc["startTime"])
    gate_local = day - pd.Timedelta(days=1) + _parse_cutoff(cutoff)
    gate = gate_local.dt.tz_localize(LONDON, ambiguous=True, nonexistent="shift_forward").dt.tz_convert("UTC")
    ok = fc[fc["publishTime"] <= gate]
    out = ok.sort_values("publishTime").groupby("startTime", as_index=False).last()
    out["horizon_h"] = (out["startTime"] - out["publishTime"]) / pd.Timedelta(hours=1)
    return out


def latest_at_horizon(fc: pd.DataFrame, horizon_h: float) -> pd.DataFrame:
    """For each target: the most recent forecast that was already published at least
    `horizon_h` hours before the target started."""
    h = (fc["startTime"] - fc["publishTime"]) / pd.Timedelta(hours=1)
    ok = fc[h >= horizon_h]
    out = ok.sort_values("publishTime").groupby("startTime", as_index=False).last()
    out["horizon_h"] = (out["startTime"] - out["publishTime"]) / pd.Timedelta(hours=1)
    return out


def pair_with_actuals(sel: pd.DataFrame, ac: pd.DataFrame) -> pd.DataFrame:
    df = sel.merge(ac, on="startTime", how="inner")
    df["error"] = df["forecast_mw"] - df["actual_mw"]
    df["day"] = delivery_day(df["startTime"])
    return df


def metrics(df: pd.DataFrame) -> dict:
    """Headline accuracy metrics for a paired frame (needs forecast_mw, actual_mw, error)."""
    if df.empty:
        return {"n": 0}
    e = df["error"].to_numpy()
    act = df["actual_mw"].to_numpy()
    q = np.quantile(e, [0.05, 0.10, 0.50, 0.90, 0.95])
    return {
        "n": int(len(df)),
        "mae_mw": float(np.mean(np.abs(e))),
        "rmse_mw": float(np.sqrt(np.mean(e**2))),
        "bias_mw": float(np.mean(e)),
        "wmape_pct": float(np.sum(np.abs(e)) / max(np.sum(act), 1e-9) * 100),
        "mean_actual_mw": float(np.mean(act)),
        "p5_error_mw": float(q[0]), "p10_error_mw": float(q[1]), "median_error_mw": float(q[2]),
        "p90_error_mw": float(q[3]), "p95_error_mw": float(q[4]),
        "over_forecast_share_pct": float(np.mean(e > 0) * 100),
        "max_over_mw": float(e.max()), "max_under_mw": float(e.min()),
    }


def by_day(df: pd.DataFrame) -> list[dict]:
    rows = []
    for d, g in df.groupby("day"):
        m = metrics(g)
        rows.append({"day": d.strftime("%Y-%m-%d"), **{k: m[k] for k in
                     ("n", "mae_mw", "rmse_mw", "bias_mw", "wmape_pct", "mean_actual_mw")}})
    return rows


def by_hour(df: pd.DataFrame) -> list[dict]:
    hr = df["startTime"].dt.tz_convert(LONDON).dt.hour
    rows = []
    for h, g in df.groupby(hr):
        m = metrics(g)
        rows.append({"hour": int(h), "n": m["n"], "mae_mw": m["mae_mw"], "bias_mw": m["bias_mw"],
                     "p10_error_mw": m["p10_error_mw"], "p90_error_mw": m["p90_error_mw"]})
    return rows


def error_histogram(df: pd.DataFrame, bin_mw: int = 250) -> list[dict]:
    if df.empty:
        return []
    e = df["error"].to_numpy()
    lo = np.floor(e.min() / bin_mw) * bin_mw
    hi = np.ceil(e.max() / bin_mw) * bin_mw + bin_mw
    edges = np.arange(lo, hi + 1, bin_mw)
    counts, edges = np.histogram(e, bins=edges)
    return [{"bin_start": float(edges[i]), "bin_end": float(edges[i + 1]),
             "label": f"{int(edges[i])}", "count": int(c)} for i, c in enumerate(counts)]


def by_horizon(fc: pd.DataFrame, ac: pd.DataFrame, horizons=range(1, 49),
               day_min=None, day_max=None) -> list[dict]:
    rows = []
    for h in horizons:
        df = pair_with_actuals(latest_at_horizon(fc, h), ac)
        df = restrict_days(df, day_min, day_max)
        if df.empty:
            continue
        m = metrics(df)
        rows.append({"horizon_h": h, "n": m["n"], "mae_mw": m["mae_mw"], "rmse_mw": m["rmse_mw"],
                     "bias_mw": m["bias_mw"], "wmape_pct": m["wmape_pct"]})
    return rows


def restrict_days(df: pd.DataFrame, day_min, day_max) -> pd.DataFrame:
    if df.empty:
        return df
    if day_min is not None:
        df = df[df["day"] >= pd.Timestamp(day_min)]
    if day_max is not None:
        df = df[df["day"] <= pd.Timestamp(day_max)]
    return df


# ---------------------------------------------------------------- planning band
def planning_band(day_pairs_history: pd.DataFrame, target: pd.DataFrame,
                  lo_q: float = 0.10, hi_q: float = 0.90, min_per_block: int = 24) -> pd.DataFrame:
    """Empirical P10/P90 range of ACTUAL wind around the day-ahead forecast.

    actual = forecast - error, so P10(actual) = forecast - Q90(error).
    Error quantiles come from `day_pairs_history` (previous delivery days only, so
    there is no look-ahead) pooled in 4-hour blocks; falls back to all history when a
    block has too few samples. Wind is clipped at 0 MW.
    """
    t = target.copy()
    t["block"] = t["startTime"].dt.tz_convert(LONDON).dt.hour // 4
    if day_pairs_history.empty:
        t["p10_mw"] = np.nan
        t["p90_mw"] = np.nan
        return t
    hist = day_pairs_history.copy()
    hist["block"] = hist["startTime"].dt.tz_convert(LONDON).dt.hour // 4
    overall = hist["error"].quantile([lo_q, hi_q])
    qs = {}
    for b, g in hist.groupby("block"):
        src = g["error"] if len(g) >= min_per_block else hist["error"]
        qs[b] = src.quantile([lo_q, hi_q])
    q_lo = t["block"].map(lambda b: qs.get(b, overall)[lo_q])
    q_hi = t["block"].map(lambda b: qs.get(b, overall)[hi_q])
    t["p10_mw"] = (t["forecast_mw"] - q_hi).clip(lower=0)
    t["p90_mw"] = (t["forecast_mw"] - q_lo).clip(lower=0)
    return t


def block_summary(df: pd.DataFrame) -> list[dict]:
    """Six-hour London blocks: energy (MWh) the buyer can count on."""
    out = []
    local_h = df["startTime"].dt.tz_convert(LONDON).dt.hour
    for b, label in enumerate(["00-06", "06-12", "12-18", "18-24"]):
        g = df[(local_h // 6) == b]
        if g.empty:
            continue
        row = {"block": label, "mean_forecast_mw": float(g["forecast_mw"].mean()),
               "forecast_mwh": float(g["forecast_mw"].sum() * HALF_HOUR_H)}
        if "p10_mw" in g and g["p10_mw"].notna().any():
            row["p10_mwh"] = float(g["p10_mw"].sum() * HALF_HOUR_H)
            row["p90_mwh"] = float(g["p90_mw"].sum() * HALF_HOUR_H)
        if "actual_mw" in g and g["actual_mw"].notna().all():
            row["actual_mwh"] = float(g["actual_mw"].sum() * HALF_HOUR_H)
        out.append(row)
    return out
