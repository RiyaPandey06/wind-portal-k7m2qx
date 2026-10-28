import { useEffect, useState } from "react";
import { get } from "./api.js";

export function useFetch(path, params) {
  const [state, set] = useState({ data: null, error: null, loading: true });
  const key = path + JSON.stringify(params);
  useEffect(() => {
    let live = true;
    set((s) => ({ ...s, loading: true, error: null }));
    get(path, params)
      .then((data) => live && set({ data, error: null, loading: false }))
      .catch((error) => live && set({ data: null, error: error.message, loading: false }));
    return () => { live = false; };
  }, [key]);
  return state;
}
