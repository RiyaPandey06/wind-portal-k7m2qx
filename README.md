# Wind Forecast Desk

Web app for a UK utility's day-ahead power-purchasing team. It shows (1) the latest national
wind-generation forecast that was actually available when the day-ahead decision had to be made
and (2) how accurate those forecasts have been, so the quantified error can feed the buying decision.

* **Live app (Vercel):** `<ADD VERCEL URL AFTER DEPLOY>`
* **Stack:** React (Vite + Recharts) · Python (FastAPI + pandas) · Docker image for local/reviewer runs · hosted on Vercel (static frontend + Python serverless function)
* **AI disclosure:** this project was built with the assistance of an AI tool (Anthropic Claude).
  All logic was reviewed and is covered by the unit tests in `backend/tests`.

## Data (Elexon Insights API, no key required)

| Purpose | Dataset | Fields used |
|---|---|---|
| Actual wind | `FUELHH` stream, `fuelType=WIND` | `startTime`, `generation` |
| Forecast wind | `WINDFOR` stream | `startTime`, `publishTime`, `generation` |

Scope: purchase decisions made **1-31 Jan 2026** (decision on D-1, delivery on D, so deliveries
2 Jan - 1 Feb 2026). Change with `DECISION_START` / `DECISION_END` env vars.

## Key modelling decisions

1. **Information set = the gate.** For each half-hour of delivery day D we take the most recent
   `WINDFOR` forecast with `publishTime <= D-1 HH:MM` (London time). Default gate 09:00 (conservative
   vs. the ~09:20 EPEX / 09:50 N2EX auction closes); selectable in the UI. Later forecasts are never
   used, so the accuracy numbers are not flattered by hindsight.
2. **Error = forecast - actual.** Positive = wind over-forecast = buyer is short (the costly side).
3. **Metrics:** MAE, RMSE, bias, WMAPE (sum|e| / sum actual), error quantiles P5/P10/P50/P90/P95,
   by day, by hour of day, error histogram, and an accuracy-vs-lead-time curve (1-48 h).
4. **Plan-on wind (P10)**: forecast shifted by the empirical error quantiles (4-hour blocks of the day),
   computed from *previous delivery days only* (no look-ahead). Falls back to all other days when
   <3 days of history exist (flagged in the API/UI).
5. Timestamps are stored in UTC; delivery days and hour-of-day are London-local.

### Known limitations (be upfront with the client)
* `FUELHH` WIND is transmission-metered wind; embedded wind is not included, and `WINDFOR` is a
  national forecast whose exact scope should be confirmed with Elexon/NESO. Part of the measured
  "error" may be a definitional difference rather than forecast skill.
* One month of data: quantiles are indicative, not statistically robust.
* Demand and prices are out of scope, so the app reports wind to count on, not a MWh-to-buy figure.

## Repository layout

```
backend/app/elexon.py     Elexon client (retries, daily chunking, dedupe)
backend/app/analysis.py   pure pandas logic: gate selection, metrics, planning band
backend/app/store.py      loads the CSV snapshot
backend/app/main.py       FastAPI: /api/meta, /api/dayahead, /api/accuracy, /api/accuracy/horizon-curve; serves SPA
backend/tests/            unit tests (gate leakage, horizon, error sign, band)
frontend/src/             React: App, DayAhead, Accuracy, shared UI
scripts/fetch_data.py     downloads Elexon data into data/*.csv (+ meta.json)
scripts/make_synthetic.py TEST FIXTURE ONLY - UI shows a warning banner on synthetic data
api/index.py              Vercel serverless entry point (exposes the FastAPI app)
vercel.json, requirements.txt, .python-version   Vercel build/runtime config (root requirements.txt = Vercel deps)
Dockerfile, docker-compose.yml   single-image build for local / reviewer use
```

## Run it

```bash
# 1) get real data (needs internet)
pip install -r backend/requirements.txt
python scripts/fetch_data.py            # writes data/wind_forecast.csv, wind_actual.csv, meta.json

# 2a) Docker (API + built UI on :8000)
docker compose up --build               # http://localhost:8000

# 2b) or dev mode
cd backend && uvicorn app.main:app --reload          # :8000
cd frontend && npm install && npm run dev            # :5173 (proxies /api)

# tests
cd backend && pytest
```

## Deploy (Vercel)

Vercel does not run Docker containers, so the hosted version runs the same code differently:
the React build is served as static files and `api/index.py` exposes the FastAPI app as a Python
serverless function. `vercel.json` rewrites `/api/*` to it and bundles `data/*.csv` and `backend/app`
into the function. The Docker image remains the way to run the whole app locally.

1. Run `python scripts/fetch_data.py` and **commit `data/*.csv`** (the serverless build does not fetch data).
2. Push to GitHub, then on vercel.com: *Add New > Project > import the repo*, Framework Preset **Other**,
   leave the build settings alone (they come from `vercel.json`), Deploy.
3. CLI alternative: `npm i -g vercel && vercel login && vercel --prod`.
