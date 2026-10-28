import React, { useState } from "react";
import { ResponsiveContainer, ComposedChart, Area, Line, XAxis, YAxis, Tooltip, Legend, CartesianGrid } from "recharts";
import { useFetch } from "./useFetch.js";
import { Kpi, Card, Status } from "./ui.jsx";
import { mw, gwh, londonTime, londonDateTime } from "./api.js";

export default function DayAhead({ meta, cutoff }) {
  const [date, setDate] = useState("2026-01-15");
  const s = useFetch("/dayahead", { delivery_date: date, cutoff });
  const d = s.data;
  const rows = d?.series.map((p) => ({
    ...p, label: londonTime(p.t), band: p.p10_mw == null ? null : [p.p10_mw, p.p90_mw],
  }));

  return (
    <>
      <section className="card gate">
        <label>
          Delivery day
          <input type="date" value={date} min={meta.first_delivery_day} max={meta.last_delivery_day}
                 onChange={(e) => e.target.value && setDate(e.target.value)} />
        </label>
        {d && <span className="hint">
          Decision taken {d.decision_time_london} (London). Forecasts used were published{" "}
          {londonDateTime(d.forecast_published_min)} – {londonDateTime(d.forecast_published_max)}.
        </span>}
      </section>
      <Status s={s} />
      {d && (
        <>
          <div className="kpis">
            <Kpi label="Forecast wind energy" value={gwh(d.summary.forecast_mwh)} note="sum of 48 half-hours" />
            <Kpi label="Plan-on wind (P10)" value={gwh(d.summary.p10_mwh)} tone="good"
                 note="90% confident actual wind ≥ this" />
            <Kpi label="Peak / minimum forecast" value={`${mw(d.summary.peak_forecast_mw)} / ${mw(d.summary.min_forecast_mw)}`} />
            <Kpi label="Actual wind (hindsight)" value={gwh(d.summary.actual_mwh)}
                 note={d.day_accuracy ? `MAE ${mw(d.day_accuracy.mae_mw)} · bias ${mw(d.day_accuracy.bias_mw)}` : "not yet available"} />
          </div>

          <Card title="Wind forecast available at the gate vs outturn"
                sub={`Shaded band = empirical P10–P90 range of actual wind, from forecast errors on ${
                  d.band_basis === "previous_days" ? "earlier delivery days only (no look-ahead)" : "all other days (little history yet)"}.`}>
            <ResponsiveContainer width="100%" height={380}>
              <ComposedChart data={rows} margin={{ top: 10, right: 20, left: 10, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="label" interval={5} />
                <YAxis tickFormatter={(v) => (v / 1000).toFixed(0) + " GW"} />
                <Tooltip formatter={(v) => (Array.isArray(v) ? v.map(Math.round).join(" – ") : Math.round(v)) + " MW"} />
                <Legend />
                <Area dataKey="band" name="P10–P90 range" stroke="none" fill="#2f80ed" fillOpacity={0.15} />
                <Line dataKey="forecast_mw" name="Forecast (at gate)" stroke="#2f80ed" dot={false} strokeWidth={2} />
                <Line dataKey="actual_mw" name="Actual" stroke="#e8590c" dot={false} strokeWidth={2} />
              </ComposedChart>
            </ResponsiveContainer>
          </Card>

          <Card title="Energy by block (what you can count on)">
            <table>
              <thead><tr><th>London block</th><th>Mean forecast</th><th>Forecast</th><th>Plan-on (P10)</th><th>Upside (P90)</th><th>Actual</th></tr></thead>
              <tbody>
                {d.blocks.map((b) => (
                  <tr key={b.block}>
                    <td>{b.block}h</td><td>{mw(b.mean_forecast_mw)}</td><td>{gwh(b.forecast_mwh)}</td>
                    <td>{gwh(b.p10_mwh)}</td><td>{gwh(b.p90_mwh)}</td><td>{gwh(b.actual_mwh)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>
        </>
      )}
    </>
  );
}
