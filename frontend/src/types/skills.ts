export interface Run {
  id: number;
  slot: string;
  status: 'running' | 'success' | 'failed';
  started_at: string;
  finished_at: string | null;
  candidate_count: number;
  matched_count: number;
  error: string | null;
}

export interface Snapshot {
  id: number;
  rank?: number;
  repo_id: number;
  full_name: string;
  url: string;
  description: string;
  stars: number;
  forks: number;
  delta_24h: number | null;
  language: string | null;
  license: string | null;
  pushed_at: string | null;
  observed_at: string;
  baseline_at: string | null;
  evidence: string;
  readme?: string;
  categories: string[];
  installation: string;
}

export interface Board {
  run: Run | null;
  items: Snapshot[];
}
