import React, { useState } from "react";
import { ResponsiveContainer, BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, CartesianGrid, Legend, ReferenceLine } from "recharts";
import { useFetch } from "./useFetch.js";
import { Kpi, Card, Status } from "./ui.jsx";
import { mw } from "./api.js";

const pct = (v) => (v == null ? "–" : v.toFixed(1) + " %");

export default function Accuracy({ cutoff }) {
  const [mode, setMode] = useState("dayahead");
  const [horizon, setHorizon] = useState(24);
  const acc = useFetch("/accuracy", { mode, cutoff, horizon });
  const curve = useFetch("/accuracy/horizon-curve", {});
  const o = acc.data?.overall;

  return (
    <>
      <section className="card gate">
        <label>
          Evaluate
          <select value={mode} onChange={(e) => setMode(e.target.value)}>
            <option value="dayahead">Day-ahead decision (forecast available at gate)</option>
            <option value="horizon">Fixed lead time before delivery</option>
          </select>
        </label>
        {mode === "horizon" && (
          <label>
            Lead time: {horizon} h
            <input type="range" min="1" max="48" value={horizon} onChange={(e) => setHorizon(+e.target.value)} />
          </label>
        )}
        <span className="hint">
          Error = forecast − actual. Positive means wind was over-forecast (risk: you bought too little elsewhere).
        </span>
      </section>
      <Status s={acc} />
      {o && (
        <>
          <div className="kpis">
            <Kpi label="MAE" value={mw(o.mae_mw)} note={`${o.n.toLocaleString()} half-hours`} />
            <Kpi label="RMSE" value={mw(o.rmse_mw)} />
            <Kpi label="Bias" value={mw(o.bias_mw)} note={o.bias_mw > 0 ? "over-forecasts on average" : "under-forecasts on average"} />
            <Kpi label="WMAPE" value={pct(o.wmape_pct)} note="Σ|error| / Σ actual" />
            <Kpi label="Shortfall risk (P90)" value={mw(o.p90_error_mw)} tone="warn"
                 note="in 10% of periods wind was over-forecast by at least this" />
            <Kpi label="Surplus risk (P10)" value={mw(-o.p10_error_mw)} note="in 10% of periods wind was under-forecast by at least this" />
          </div>

          <Card title="Daily error" sub="Mean absolute error per delivery day (MW)">
            <ResponsiveContainer width="100%" height={260}>
              <BarChart data={acc.data.daily}><CartesianGrid strokeDasharray="3 3" />
                <XAxis dataKey="day" tickFormatter={(d) => d.slice(8)} /><YAxis />
                <Tooltip formatter={(v) => Math.round(v) + " MW"} />
                <Legend />
                <Bar dataKey="mae_mw" name="MAE" fill="#2f80ed" />
                <Bar dataKey="bias_mw" name="Bias" fill="#e8590c" />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          <div className="grid2">
            <Card title="Error distribution" sub="Histogram of forecast − actual (MW)">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={acc.data.histogram}><CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="label" interval="preserveStartEnd" /><YAxis />
                  <Tooltip /><ReferenceLine x="0" stroke="#000" />
                  <Bar dataKey="count" fill="#6c5ce7" />
                </BarChart>
              </ResponsiveContainer>
            </Card>
            <Card title="Error by hour of day (London)">
              <ResponsiveContainer width="100%" height={260}>
                <BarChart data={acc.data.by_hour}><CartesianGrid strokeDasharray="3 3" />
                  <XAxis dataKey="hour" /><YAxis />
                  <Tooltip formatter={(v) => Math.round(v) + " MW"} /><Legend />
                  <Bar dataKey="mae_mw" name="MAE" fill="#2f80ed" />
                  <Bar dataKey="bias_mw" name="Bias" fill="#e8590c" />
                </BarChart>
              </ResponsiveContainer>
            </Card>
          </div>

          <Card title="Error quantiles (MW)" sub="Use these as the quantified uncertainty around the forecast.">
            <table>
              <thead><tr><th>P5</th><th>P10</th><th>Median</th><th>P90</th><th>P95</th></tr></thead>
              <tbody><tr>{[o.p5_error_mw, o.p10_error_mw, o.median_error_mw, o.p90_error_mw, o.p95_error_mw].map((v, i) => <td key={i}>{mw(v)}</td>)}</tr></tbody>
            </table>
          </Card>
        </>
      )}

      <Card title="How quickly does accuracy improve as delivery approaches?"
            sub="MAE for the latest forecast published at least N hours before each half-hour">
        <Status s={curve} />
        {curve.data && (
          <ResponsiveContainer width="100%" height={280}>
            <LineChart data={curve.data.curve}><CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="horizon_h" label={{ value: "lead time (h)", position: "insideBottom", offset: -2 }} />
              <YAxis /><Tooltip formatter={(v) => Math.round(v) + " MW"} /><Legend />
              <Line dataKey="mae_mw" name="MAE" stroke="#2f80ed" dot={false} strokeWidth={2} />
              <Line dataKey="rmse_mw" name="RMSE" stroke="#6c5ce7" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        )}
      </Card>
    </>
  );
}
