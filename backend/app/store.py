"""Loads the CSV snapshot once and exposes it. Kept separate from analysis (pure)."""
from __future__ import annotations

import json
from functools import lru_cache

import pandas as pd

from . import config


class DataNotReady(RuntimeError):
    pass


@lru_cache(maxsize=1)
def load() -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    f, a, m = (config.DATA_DIR / n for n in ("wind_forecast.csv", "wind_actual.csv", "meta.json"))
    if not (f.exists() and a.exists()):
        raise DataNotReady("No data snapshot found. Run `python scripts/fetch_data.py` first.")
    fc = pd.read_csv(f, parse_dates=["startTime", "publishTime"])
    ac = pd.read_csv(a, parse_dates=["startTime"])
    for df in (fc, ac):
        df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    fc["publishTime"] = pd.to_datetime(fc["publishTime"], utc=True)
    meta = json.loads(m.read_text()) if m.exists() else {}
    return fc, ac, meta
