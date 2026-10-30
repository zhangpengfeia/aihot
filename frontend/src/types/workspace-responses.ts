import type { Run, Snapshot } from './skills';
export interface Summary {
  current: Run | null;
  previous: Run | null;
  new_entries: Snapshot[];
  risers: (Snapshot & { previous_rank: number; rank_change: number })[];
  growth: Snapshot[];
}

export interface Status {
  schedule: string;
  next_scheduled_at: string;
  server_time: string;
  latest: Run | null;
  last_success: Run | null;
  last_failure: Run | null;
  recent_runs: Run[];
  total_successful_runs: number;
  knowledge_sources: {
    name: string;
    status: string;
    last_attempt: string | null;
    last_success: string | null;
    error: string | null;
  }[];
}
