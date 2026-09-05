// Mirrors scripts/export_dashboard_data.py's JSON shape exactly -- one
// source of truth on the Python side, typed here so a shape drift shows up
// as a compile error instead of a silent undefined in the UI.

export interface EvidenceLine {
  text: string;
  direction: "raised" | "lowered" | null;
  magnitude: number | null;
}

export interface GraphSignal {
  found: boolean;
  source?: string;
  shared_card_count?: number;
  shared_addr_count?: number;
  neighbor_fraud_count?: number;
  other_fraud_in_component?: number;
  connected_component_size?: number;
}

export interface RedTeamResult {
  pre: number;
  post: number;
  evaded: boolean;
}

export interface Transaction {
  id: number;
  amount: number;
  score: number;
  threshold: number;
  verdict: "block" | "flag" | "allow";
  verdict_bucket: "flag/block" | "allow";
  actual: "fraud" | "legit";
  evidence: EvidenceLine[];
  graph: GraphSignal;
  red_team: RedTeamResult | null;
}

export interface ModelMetrics {
  precision: number;
  recall: number;
  f1: number;
  roc_auc: number;
  pr_auc: number;
  evasion_success_rate: number;
}

export interface Metrics {
  baseline: ModelMetrics;
  hardened: ModelMetrics;
  attack_sample_size: number;
  note: string;
}

export interface DashboardData {
  generated_at: string;
  n_sample: number;
  n_red_team: number;
  metrics: Metrics | null;
  transactions: Transaction[];
}
