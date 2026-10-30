/** 统一 HTTP 请求与错误处理。 */
export async function get<T>(path: string, signal?: AbortSignal): Promise<T> {
  const response = await fetch(`/api${path}`, { signal });
  if (!response.ok)
    throw new Error(`读取失败（${response.status}），请检查后端服务或选择已完成批次。`);
  return response.json() as Promise<T>;
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
  return response.status === 204 ? (undefined as T) : (response.json() as Promise<T>);
}
