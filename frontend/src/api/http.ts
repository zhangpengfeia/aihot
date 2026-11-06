/** 统一 HTTP 请求与错误处理，附带进程内只读缓存与后台静默刷新。 */

type CacheEntry = { data: unknown; at: number };
const memoryCache = new Map<string, CacheEntry>();
// 只读接口数据半静态（榜单每天、热搜/知识每半小时更新），缓存 5 分钟。
const CACHE_TTL = 5 * 60_000;

export function readCache<T>(path: string): T | undefined {
  const entry = memoryCache.get(path);
  if (entry && Date.now() - entry.at < CACHE_TTL) return entry.data as T;
  if (entry) memoryCache.delete(path);
  return undefined;
}

export function invalidateCache(): void {
  memoryCache.clear();
}

function refreshInBackground(path: string, signal?: AbortSignal): void {
  fetch(`/api${path}`, { signal })
    .then((response) => (response.ok ? (response.json() as Promise<unknown>) : undefined))
    .then((json) => {
      if (json !== undefined) memoryCache.set(path, { data: json, at: Date.now() });
    })
    .catch(() => {
      // 后台刷新失败静默忽略，保留旧缓存，下次周期继续重试。
    });
}

async function request<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api${path}`, { signal });
  if (!response.ok)
    throw new Error(`读取失败（${response.status}），请检查后端服务或选择已完成批次。`);
  return response.json() as Promise<T>;
}

export async function get<T>(
  path: string,
  signal?: AbortSignal,
  opts?: { cache?: boolean },
): Promise<T> {
  if (opts?.cache) {
    const cached = readCache<T>(path);
    if (cached !== undefined) {
      // 命中缓存立即返回，同时后台刷新，供下次访问使用；期间不转圈。
      refreshInBackground(path, signal);
      return cached;
    }
  }
  const data = await request<T>(path, signal);
  if (opts?.cache) memoryCache.set(path, { data, at: Date.now() });
  return data;
}

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
  // 写操作成功后清空只读缓存，避免展示过期数据。
  invalidateCache();
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>);
}
