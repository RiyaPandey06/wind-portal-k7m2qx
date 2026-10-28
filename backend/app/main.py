"""FastAPI app: JSON API under /api, React build served from /."""
from __future__ import annotations

from functools import lru_cache

import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from . import analysis as an
from . import config
from .store import DataNotReady, load

app = FastAPI(title="Wind forecast accuracy portal", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["GET"])

CUTOFF_RE = r"^([01]\d|2[0-3]):[0-5]\d$"


def _data():
    try:
        return load()
    except DataNotReady as e:
        raise HTTPException(503, str(e))


def _iso(ts: pd.Series) -> list[str]:
    return ts.dt.strftime("%Y-%m-%dT%H:%M:%SZ").tolist()


def _clean(v):
    return None if (isinstance(v, float) and np.isnan(v)) else v


def _delivery_range():
    s = pd.Timestamp(config.DECISION_START) + pd.Timedelta(days=1)
    e = pd.Timestamp(config.DECISION_END) + pd.Timedelta(days=1)
    return s, e


@lru_cache(maxsize=64)
def _dayahead_pairs(cutoff: str) -> pd.DataFrame:
    fc, ac, _ = _data()
    s, e = _delivery_range()
    sel = an.latest_at_dayahead_gate(fc, cutoff)
    return an.restrict_days(an.pair_with_actuals(sel, ac), s, e)


@lru_cache(maxsize=64)
def _horizon_pairs(h: float) -> pd.DataFrame:
    fc, ac, _ = _data()
    s, e = _delivery_range()
    return an.restrict_days(an.pair_with_actuals(an.latest_at_horizon(fc, h), ac), s, e)


def _pairs(mode: str, cutoff: str, horizon: float) -> pd.DataFrame:
    return _dayahead_pairs(cutoff) if mode == "dayahead" else _horizon_pairs(horizon)


@app.get("/api/meta")
def meta():
    fc, ac, m = _data()
    s, e = _delivery_range()
    return {**m, "default_cutoff": config.DEFAULT_CUTOFF,
            "first_delivery_day": s.strftime("%Y-%m-%d"), "last_delivery_day": e.strftime("%Y-%m-%d"),
            "forecast_rows": int(len(fc)), "forecast_publish_times": int(fc["publishTime"].nunique()),
            "actual_rows": int(len(ac))}


@app.get("/api/dayahead")
def dayahead(delivery_date: str = Query(..., pattern=r"^\d{4}-\d{2}-\d{2}$"),
             cutoff: str = Query(config.DEFAULT_CUTOFF, pattern=CUTOFF_RE)):
    """The forecast a trader actually has at the day-ahead gate for `delivery_date`."""
    fc, ac, _ = _data()
    day = pd.Timestamp(delivery_date)
    sel = an.latest_at_dayahead_gate(fc, cutoff)
    sel = sel[an.delivery_day(sel["startTime"]) == day]
    if sel.empty:
        raise HTTPException(404, f"No forecast available at the {cutoff} gate for {delivery_date}")
    df = sel.merge(ac, on="startTime", how="left")
    hist = _dayahead_pairs(cutoff)
    hist = hist[hist["day"] < day]
    if hist["day"].nunique() < 3:  # too little history: use every other day (flagged in response)
        hist, hist_mode = _dayahead_pairs(cutoff)[lambda d: d["day"] != day], "all_other_days"
    else:
        hist_mode = "previous_days"
    df = an.planning_band(hist, df)
    has_actual = bool(df["actual_mw"].notna().all())
    if has_actual:
        df["error"] = df["forecast_mw"] - df["actual_mw"]
    series = [{"t": t, "forecast_mw": float(f), "actual_mw": _clean(float(a)), "p10_mw": _clean(float(p10)),
               "p90_mw": _clean(float(p90))}
              for t, f, a, p10, p90 in zip(_iso(df["startTime"]), df["forecast_mw"], df["actual_mw"],
                                           df["p10_mw"], df["p90_mw"])]
    pub = sel["publishTime"]
    return {
        "delivery_date": delivery_date, "cutoff": cutoff,
        "decision_time_london": f"{(day - pd.Timedelta(days=1)).strftime('%Y-%m-%d')} {cutoff}",
        "forecast_published_min": pub.min().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "forecast_published_max": pub.max().strftime("%Y-%m-%dT%H:%M:%SZ"),
        "n_periods": int(len(df)),
        "summary": {
            "forecast_mwh": float(df["forecast_mw"].sum() * 0.5),
            "mean_forecast_mw": float(df["forecast_mw"].mean()),
            "peak_forecast_mw": float(df["forecast_mw"].max()),
            "min_forecast_mw": float(df["forecast_mw"].min()),
            "p10_mwh": _clean(float(df["p10_mw"].sum() * 0.5)),
            "p90_mwh": _clean(float(df["p90_mw"].sum() * 0.5)),
            "actual_mwh": float(df["actual_mw"].sum() * 0.5) if has_actual else None,
        },
        "band_basis": hist_mode,
        "blocks": [{k: _clean(v) for k, v in b.items()} for b in an.block_summary(df)],
        "day_accuracy": an.metrics(df.dropna(subset=["actual_mw"])) if has_actual else None,
        "series": series,
    }


@app.get("/api/accuracy")
def accuracy(mode: str = Query("dayahead", pattern="^(dayahead|horizon)$"),
             cutoff: str = Query(config.DEFAULT_CUTOFF, pattern=CUTOFF_RE),
             horizon: float = Query(24, ge=0.5, le=72)):
    df = _pairs(mode, cutoff, horizon)
    if df.empty:
        raise HTTPException(404, "No overlapping forecast/actual data for these settings")
    return {"mode": mode, "cutoff": cutoff, "horizon_h": horizon,
            "overall": an.metrics(df), "daily": an.by_day(df),
            "by_hour": an.by_hour(df), "histogram": an.error_histogram(df)}


@app.get("/api/accuracy/horizon-curve")
def horizon_curve():
    fc, ac, _ = _data()
    s, e = _delivery_range()
    return {"curve": an.by_horizon(fc, ac, day_min=s, day_max=e)}


@app.get("/api/health")
def health():
    return {"ok": True}


# ------------------------------------------------------------------ static SPA
if config.STATIC_DIR.exists():
    app.mount("/assets", StaticFiles(directory=config.STATIC_DIR / "assets"), name="assets")

    @app.get("/{path:path}", include_in_schema=False)
    def spa(path: str):
        f = config.STATIC_DIR / path
        return FileResponse(f if f.is_file() else config.STATIC_DIR / "index.html")
