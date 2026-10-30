import { useEffect,useState } from 'react';
import { get } from '../api/http';
export function useResource<T>(path: string, tick: number) {
  const [data, setData] = useState<T | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [revision, setRevision] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    get<T>(path, controller.signal)
      .then(setData)
      .catch((e) => {
        if (!controller.signal.aborted) setError((e as Error).message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [path, tick, revision]);
  return { data, loading, error, refresh: () => setRevision((v) => v + 1) };
}
