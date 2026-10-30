export interface ManagedSource {
  adapter: string;
  item_limit: number;
  options: Record<string, string>;
  id: number;
  name: string;
  url: string;
  category: string;
  display_category: string;
  region: '国内' | '国外';
  topic_kind: '热点候选' | '知识探索';
  enabled: boolean;
  collected_count: number;
  status: string;
  last_attempt: string | null;
  last_success: string | null;
  error: string | null;
  last_test_at: string | null;
  last_test_error: string | null;
  last_test_count: number | null;
}

export interface CategoryRow {
  name: string;
  canonical_name: string;
  topic_count: number;
  total_count: number;
  hidden: boolean;
  is_alias: boolean;
}

export interface CategoryResponse {
  items: CategoryRow[];
  catalog: {
    status: string;
    source_name: string;
    source_url: string;
    updated_at: string | null;
    error: string | null;
  };
}

export interface Preview {
  ok: boolean;
  error: string | null;
  checked_at: string;
  item_count: number;
  items: { title: string; url: string; published_at: string | null }[];
}
