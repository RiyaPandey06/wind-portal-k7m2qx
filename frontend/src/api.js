export async function get(path, params = {}) {
  const qs = new URLSearchParams(params).toString();
  const res = await fetch(`/api${path}${qs ? "?" + qs : ""}`);
  if (!res.ok) {
    let msg = res.statusText;
    try { msg = (await res.json()).detail || msg; } catch {}
    throw new Error(msg);
  }
  return res.json();
}

// Hook-free helpers
export const mw = (v) => (v == null ? "–" : Math.round(v).toLocaleString("en-GB") + " MW");
export const gwh = (v) => (v == null ? "–" : (v / 1000).toFixed(1) + " GWh");
export const londonTime = (iso) =>
  new Date(iso).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "Europe/London" });
export const londonDateTime = (iso) =>
  new Date(iso).toLocaleString("en-GB", { dateStyle: "medium", timeStyle: "short", timeZone: "Europe/London" });
