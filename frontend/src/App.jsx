import React, { useState } from "react";
import { useFetch } from "./useFetch.js";
import DayAhead from "./DayAhead.jsx";
import Accuracy from "./Accuracy.jsx";

export default function App() {
  const [tab, setTab] = useState("day");
  const [cutoff, setCutoff] = useState("09:00");
  const meta = useFetch("/meta", {});

  return (
    <div className="app">
      <header>
        <div>
          <h1>Wind Forecast Desk</h1>
          <p className="sub">GB national wind · day-ahead purchase support · Elexon BMRS data</p>
        </div>
        <nav>
          <button className={tab === "day" ? "on" : ""} onClick={() => setTab("day")}>Day-ahead forecast</button>
          <button className={tab === "acc" ? "on" : ""} onClick={() => setTab("acc")}>Forecast accuracy</button>
        </nav>
      </header>

      {meta.error && <div className="banner err">API error: {meta.error}</div>}
      {meta.data?.source === "synthetic" && (
        <div className="banner warn">SYNTHETIC TEST DATA – not real Elexon data. Do not use for decisions.</div>
      )}

      {meta.data && (
        <section className="card gate">
          <label>
            Day-ahead gate (London time, day before delivery)
            <select value={cutoff} onChange={(e) => setCutoff(e.target.value)}>
              {["08:00", "09:00", "09:20", "10:00", "12:00"].map((c) => <option key={c}>{c}</option>)}
            </select>
          </label>
          <span className="hint">
            Only forecasts published at or before the gate are treated as available to the trader.
            Accuracy is always measured against this same information set.
          </span>
        </section>
      )}

      {meta.data && tab === "day" && <DayAhead meta={meta.data} cutoff={cutoff} />}
      {meta.data && tab === "acc" && <Accuracy meta={meta.data} cutoff={cutoff} />}

      <footer>
        Data: Elexon Insights Solution (FUELHH wind outturn, WINDFOR wind forecast), transmission-metered wind only.
        Snapshot fetched {meta.data?.fetched_at ?? "–"}.
      </footer>
    </div>
  );
}
