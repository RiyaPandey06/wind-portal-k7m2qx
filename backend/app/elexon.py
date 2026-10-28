"""Thin client for the Elexon Insights (BMRS) stream endpoints. No API key needed."""
from __future__ import annotations

import time
from datetime import datetime, timedelta, timezone

import httpx
import pandas as pd

from .config import ELEXON_BASE, MAX_HORIZON_H


def _get(client: httpx.Client, path: str, params: dict, retries: int = 5) -> list[dict]:
    url = f"{ELEXON_BASE}{path}"
    for attempt in range(retries):
        try:
            r = client.get(url, params=params, timeout=60)
            if r.status_code == 429 or r.status_code >= 500:
                raise httpx.HTTPStatusError("retryable", request=r.request, response=r)
            r.raise_for_status()
            body = r.json()
            return body["data"] if isinstance(body, dict) else body
        except (httpx.TransportError, httpx.HTTPStatusError) as exc:
            if isinstance(exc, httpx.HTTPStatusError) and exc.response.status_code < 429:
                raise
            time.sleep(2**attempt)
    raise RuntimeError(f"Elexon request failed after {retries} retries: {url} {params}")


def _iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")


def fetch_wind_actuals(start: datetime, end: datetime) -> pd.DataFrame:
    """FUELHH, fuelType=WIND, half-hourly outturn (MW). One day per request."""
    rows: list[dict] = []
    with httpx.Client() as c:
        day = start
        while day < end:
            nxt = min(day + timedelta(days=1), end)
            params = {
                "settlementDateFrom": day.strftime("%Y-%m-%d"),
                "settlementDateTo": (nxt - timedelta(seconds=1)).strftime("%Y-%m-%d"),
                "fuelType": "WIND",
                "format": "json",
            }
            try:
                rows += _get(c, "/datasets/FUELHH/stream", params)
            except httpx.HTTPStatusError:
                # Fallback: some deployments expose publish-time windows instead.
                p2 = {"publishDateTimeFrom": _iso(day), "publishDateTimeTo": _iso(nxt),
                      "fuelType": "WIND", "format": "json"}
                rows += _get(c, "/datasets/FUELHH/stream", p2)
            day = nxt
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("FUELHH returned no rows")
    df = df[df["fuelType"] == "WIND"].copy()
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    # keep the latest publication for each half-hour
    df = df.sort_values("publishTime").drop_duplicates("startTime", keep="last")
    df = df.rename(columns={"generation": "actual_mw"})[["startTime", "actual_mw"]]
    return df.sort_values("startTime").reset_index(drop=True)


def fetch_wind_forecasts(pub_start: datetime, pub_end: datetime) -> pd.DataFrame:
    """WINDFOR: every forecast vintage (publishTime) for each target startTime."""
    rows: list[dict] = []
    with httpx.Client() as c:
        day = pub_start
        while day < pub_end:
            nxt = min(day + timedelta(days=1), pub_end)
            params = {"publishDateTimeFrom": _iso(day), "publishDateTimeTo": _iso(nxt),
                      "format": "json"}
            rows += _get(c, "/datasets/WINDFOR/stream", params)
            day = nxt
    df = pd.DataFrame(rows)
    if df.empty:
        raise RuntimeError("WINDFOR returned no rows")
    df["startTime"] = pd.to_datetime(df["startTime"], utc=True)
    df["publishTime"] = pd.to_datetime(df["publishTime"], utc=True)
    df = df.rename(columns={"generation": "forecast_mw"})
    df = df[["startTime", "publishTime", "forecast_mw"]]
    h = (df["startTime"] - df["publishTime"]) / pd.Timedelta(hours=1)
    df = df[(h >= 0) & (h <= MAX_HORIZON_H)]  # drop already-elapsed & very long horizons
    df = df.drop_duplicates(["startTime", "publishTime"], keep="last")
    return df.sort_values(["startTime", "publishTime"]).reset_index(drop=True)
