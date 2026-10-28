#!/usr/bin/env python
"""Download January-2026 wind actuals + forecast vintages from Elexon into data/*.csv."""
import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))
from app import config, elexon  # noqa: E402


def utc(d: str) -> datetime:
    return datetime.strptime(d, "%Y-%m-%d").replace(tzinfo=timezone.utc)


def main() -> None:
    d0, d1 = utc(config.DECISION_START), utc(config.DECISION_END)
    # decisions on D-1 for delivery on D  =>  deliveries span d0+1 .. d1+1 (inclusive)
    pub_start, pub_end = d0, d1 + timedelta(days=1)
    act_start, act_end = d0, d1 + timedelta(days=3)  # a little slack past last delivery day

    config.DATA_DIR.mkdir(parents=True, exist_ok=True)
    print("Fetching WINDFOR forecasts ...")
    fc = elexon.fetch_wind_forecasts(pub_start, pub_end)
    print(f"  {len(fc):,} rows, {fc.publishTime.nunique()} publish times")
    print("Fetching FUELHH wind actuals ...")
    ac = elexon.fetch_wind_actuals(act_start, act_end)
    print(f"  {len(ac):,} rows")
    fc.to_csv(config.DATA_DIR / "wind_forecast.csv", index=False)
    ac.to_csv(config.DATA_DIR / "wind_actual.csv", index=False)
    (config.DATA_DIR / "meta.json").write_text(json.dumps({
        "source": "elexon",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "decision_start": config.DECISION_START, "decision_end": config.DECISION_END,
    }, indent=2))
    print("Done ->", config.DATA_DIR)


if __name__ == "__main__":
    main()
