/** 接口类型集中管理，避免页面对服务器返回的数据作隐式假设。 */
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
export async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api${path}`, { signal });
  if (!response.ok)
    throw new Error(`读取失败（${response.status}），请检查后端服务或选择已完成批次。`);
  return response.json() as Promise<T>;
}
export const formatTime = (value: string | null) =>
  value
    ? new Date(value).toLocaleString('zh-CN', { timeZone: 'Asia/Shanghai', hour12: false })
    : '—';

export async function write<T>(
  path: string,
  method: 'PUT' | 'POST' | 'PATCH' | 'DELETE',
  body?: unknown,
): Promise<T> {
  const response = await fetch(`/api${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    const detail = payload?.detail;
    throw new Error(
      typeof detail === 'string' ? detail : `保存失败（${response.status}），请检查输入后重试。`,
    );
  }
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>);
}

export interface PersonalItem {
  id?: number;
  target_kind: 'repository' | 'topic';
  target_id: number;
  favorite: boolean;
  note: string;
  title: string;
  url: string;
  snapshot_id?: number;
  topic_id?: number;
  updated_at?: string;
}

export const CREATION_STAGES = ['待筛选', '待创作', '制作中', '已发布'] as const;
export interface CreationCard {
  id: number;
  topic_id: number;
  title: string;
  category: string;
  source_url: string;
  stage: (typeof CREATION_STAGES)[number];
  script: string;
  output_url: string;
  updated_at: string;
}
