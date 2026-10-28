#!/usr/bin/env python
"""TEST FIXTURE ONLY. Writes a clearly-labelled synthetic data set so the UI/tests can
run offline. NEVER use for the client demo: meta.json is stamped source=synthetic and
the UI shows a warning banner."""
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

out = Path(sys.argv[1] if len(sys.argv) > 1 else "data")
out.mkdir(exist_ok=True, parents=True)
rng = np.random.default_rng(7)
idx = pd.date_range("2026-01-01", "2026-02-04", freq="30min", tz="UTC", inclusive="left")
slow = np.cumsum(rng.normal(0, 90, len(idx)))
truth = np.clip(9000 + 3500 * np.sin(np.arange(len(idx)) / 160) + slow * 0.6, 300, 20000)
act = pd.DataFrame({"startTime": idx, "actual_mw": truth.round(1)})
rows = []
for pub in pd.date_range("2026-01-01", "2026-02-02", freq="3h", tz="UTC"):
    for k in range(0, 73 * 2):
        t = pub + pd.Timedelta(minutes=30 * k)
        if t not in idx:
            continue
        h = k / 2
        sd = 250 + 55 * h
        rows.append((t, pub, max(truth[idx.get_loc(t)] + rng.normal(0, sd), 0)))
fc = pd.DataFrame(rows, columns=["startTime", "publishTime", "forecast_mw"]).round(1)
fc.to_csv(out / "wind_forecast.csv", index=False)
act.to_csv(out / "wind_actual.csv", index=False)
(out / "meta.json").write_text(json.dumps({"source": "synthetic", "fetched_at": "n/a"}))
print("synthetic written to", out)
