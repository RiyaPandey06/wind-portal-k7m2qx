# Video script (target 9:30, hard max 10:00)

Record the screen with the live app open. Keep Part 1 free of jargon about code.
**Before recording:** replace the `[...]` placeholders with real numbers from the real January data.

## PART 1 - Client pitch (0:00-4:45)

**0:00 Hook (screen: Day-ahead tab, 15 Jan)**
"Every morning before the day-ahead gate closes, your desk has to decide how much power to buy on
top of wind. This portal shows you exactly what the wind forecast says at that moment, and how much
you can trust it."

**0:25 The problem**
"Wind is weather-driven. You commit a day early using a forecast, and if the wind falls short you
buy the gap in real time. So two things matter: what the forecast is, and how wrong it tends to be."

**0:50 Day-ahead view (pick a delivery day; point at each element)**
- "This is the forecast you'd have had at 09:00 on the day before. Not today's, not a later one. We
  only use what was published before the gate, so nothing here benefits from hindsight."
- "Blue line: forecast. Orange: what actually happened. Shaded band: the range wind stayed within 80% of the time, based on past errors."
- "The key number: *plan-on wind*, [X] GWh, is the amount you can count on with 90% confidence. Forecast
  says [Y] GWh."
- "Change the gate time and everything recalculates."

**2:00 Accuracy tab**
- "Across January, at the day-ahead gate the average miss is [MAE] MW, [WMAPE]% of generation."
- "Bias: [bias] MW, so the forecast tends to [over/under]-forecast."
- "In 1 in 10 half-hours wind came in [P90] MW below forecast. That's your shortfall risk to price in."
- Daily chart: "Some days are much harder: [worst day] was [x] times worse than a typical day."
- Hour-of-day chart: "Errors are larger at [hours]."
- Lead-time curve: "Accuracy improves sharply closer to delivery, which is the value of intraday adjustment."

**3:45 How to use it (3 bullets)**
"1) Plan to the P10 line, not the central forecast, on volatile days. 2) Hold more reserve in blocks
with wide bands. 3) Review bias weekly. Next steps: add demand and price data to turn this into a
MWh-to-buy recommendation, extend beyond one month, add regional data."

**4:30 Honest caveat (builds trust)**
"One month of data and transmission-metered wind only, so treat the quantiles as indicative. That's
the first thing we'd fix in phase two."  -> 4:45 close.

## PART 2 - Tech lead review (4:45-9:30)

**4:45 Architecture (show the README tree or a quick diagram)**
"React SPA on FastAPI, one Docker image. A fetch script snapshots Elexon data to CSV, the API loads it
into pandas, endpoints are thin wrappers over a pure analysis module. Snapshot rather than live calls:
reproducible numbers, fast demo, no dependency on Elexon uptime."

**5:30 Data model & the one idea that matters**
Open `analysis.py` -> `latest_at_dayahead_gate`.
"WINDFOR contains many forecasts for each half-hour, one per publishTime. Taking the latest overall
would leak the future into the accuracy score. I filter `publishTime <= D-1 09:00 London`, take the last
per target. `latest_at_horizon` does the same for a fixed lead time."
Show the leakage unit test.

**6:30 Metrics & the planning band**
"error = forecast - actual, so positive is the costly over-forecast. Band: actual = forecast - error, so
P10(actual) = forecast - Q90(error). Quantiles come from previous days only, pooled in 4-hour blocks."

**7:15 Backend/API** - show `/docs` (FastAPI Swagger), input validation (regex cutoff -> 422), `lru_cache`.

**7:45 Frontend** - `useFetch` hook, one component per tab, London-time formatting at the edge only.

**8:15 Quality & practices** - run `pytest` (4 tests), mention UTC internally/London for days, retries
and daily chunking in `elexon.py`, synthetic fixture clearly bannered, AI tool use disclosed in README.

**8:50 Deploy** - hosted on Vercel: static React build + `api/index.py` serverless FastAPI, `vercel.json` rewrite and bundled data CSVs; Dockerfile/compose kept for local runs (Vercel can't run containers).

**9:10 Limitations & next steps** - FUELHH vs WINDFOR scope mismatch, 1 month sample, no demand/price,
add tests for the API layer, scheduled data refresh, CI. -> end 9:30.
