import { useEffect, useRef, useState } from 'react';
import { get } from '../api/http';
export function useResource<T>(
  path: string,
  tick: number,
  { silentRefresh = false }: { silentRefresh?: boolean } = {},
) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  const loadedPath = useRef<string | null>(null);
  const lastRequest = useRef({ path, revision });
  useEffect(() => {
    const controller = new AbortController();
    const background =
      silentRefresh &&
      loadedPath.current === path &&
      lastRequest.current.path === path &&
      lastRequest.current.revision === revision;
    lastRequest.current = { path, revision };
    if (!background) {
      setLoading(true);
      setError('');
    }
    get<T>(path, controller.signal)
      .then((result) => {
        if (controller.signal.aborted) return;
        loadedPath.current = path;
        setData((previous) =>
          silentRefresh && JSON.stringify(previous) === JSON.stringify(result) ? previous : result,
        );
        setError('');
      })
      .catch((e) => {
        // 后台更新失败时保留内容，下个周期继续重试；主动查询失败仍明确提示。
        if (!controller.signal.aborted && !background) setError((e as Error).message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [path, tick, revision, silentRefresh]);
  return { data, loading, error, refresh: () => setRevision((v) => v + 1) };
}
