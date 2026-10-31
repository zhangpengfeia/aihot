export interface Topic {
  id: number;
  title: string;
  tags?: string[];
  category: string;
  region: string;
  region_basis: string;
  topic_kind: string;
  summary: string;
  video_angle: string;
  channels: { name: string; adapter: string; score: number | null }[];
  source_name: string;
  source_url: string;
  published_at: string | null;
  collected_at: string;
  summary_method: string;
  angle_method: string;
}

export interface Source {
  id?: number;
  adapter?: string;
  name: string;
  category: string;
  status: string;
  enabled?: boolean;
  display_category?: string;
  last_success: string | null;
  error: string | null;
}

export interface Meta {
  categories: string[];
  tag_groups?: Record<string, string[]>;
  tag_count?: number;
  total: number;
  category_catalog?: {
    status: 'success' | 'stale' | 'fallback';
    source_name: string;
    source_url: string;
    updated_at: string | null;
    remote_count: number;
    error: string | null;
  };
  sources: Source[];
}
