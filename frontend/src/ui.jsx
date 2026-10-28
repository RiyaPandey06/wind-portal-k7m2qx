import React from "react";

export const Kpi = ({ label, value, note, tone }) => (
  <div className={"kpi " + (tone || "")}>
    <div className="kl">{label}</div>
    <div className="kv">{value}</div>
    {note && <div className="kn">{note}</div>}
  </div>
);

export const Card = ({ title, sub, children }) => (
  <section className="card">
    <h2>{title}</h2>
    {sub && <p className="hint">{sub}</p>}
    {children}
  </section>
);

export const Status = ({ s }) => {
  if (s.loading) return <div className="muted">Loading…</div>;
  if (s.error) return <div className="banner err">{s.error}</div>;
  return null;
};
