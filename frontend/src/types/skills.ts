export interface Run {
  id: number;
  slot: string;
  scope: string | null;
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
  delta_7d: number | null;
  baseline_7d_at: string | null;
  analysis: {
    source: 'rules' | 'llm';
    version: string;
    model: string | null;
    domains: string[];
    tags: string[];
    core_features: string[];
    use_cases: string[];
    knowledge_suggestions: string[];
    evidence: string[];
  } | null;
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
