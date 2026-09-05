import { useEffect, useState } from "react";
import type { DashboardData } from "../types";

interface State {
  data: DashboardData | null;
  loading: boolean;
  error: string | null;
}

// Loads the precomputed export (public/data/dashboard.json) -- see
// scripts/export_dashboard_data.py for how it's generated and why this app
// reads a static file instead of calling a live API.
export function useDashboardData(): State {
  const [state, setState] = useState<State>({ data: null, loading: true, error: null });

  useEffect(() => {
    let cancelled = false;
    fetch(`${import.meta.env.BASE_URL}data/dashboard.json`)
      .then((res) => {
        if (!res.ok) throw new Error(`HTTP ${res.status}`);
        return res.json();
      })
      .then((data: DashboardData) => {
        if (!cancelled) setState({ data, loading: false, error: null });
      })
      .catch((err: Error) => {
        if (!cancelled) setState({ data: null, loading: false, error: err.message });
      });
    return () => {
      cancelled = true;
    };
  }, []);

  return state;
}
