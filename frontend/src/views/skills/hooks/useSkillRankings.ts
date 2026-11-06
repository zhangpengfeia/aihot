import { useEffect, useRef, useState } from 'react';
import { get, readCache } from '../../../api/http';
import type { Board, Run } from '../../../types/skills';
export function useSkillRankings(history: boolean, tick: number) {
  const [kind, setKind] = useState<'stars' | 'growth'>('stars');
  const [day, setDay] = useState('');
  const [runs, setRuns] = useState<Run[]>([]);
  const [runId, setRunId] = useState<number | undefined>();
  const [board, setBoard] = useState<Board>({ run: null, items: [] });

  const [loading, setLoading] = useState(true);
  const [runsLoading, setRunsLoading] = useState(true);
  const [error, setError] = useState('');
  const [runError, setRunError] = useState('');
  const previousQuery = useRef('');
  useEffect(() => {
    const controller = new AbortController();
    const path = `/runs?limit=100${history && day ? `&day=${day}` : ''}`;
    if (readCache(path) === undefined) setRunsLoading(true);
    setRunError('');
    get<Run[]>(path, controller.signal, { cache: true })
      .then(setRuns)
      .catch((e) => {
        if (!controller.signal.aborted) setRunError((e as Error).message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setRunsLoading(false);
      });
    return () => controller.abort();
  }, [day, tick, history]);

  useEffect(() => {
    const controller = new AbortController();
    const query = `/rankings?kind=${kind}${history ? `&run_id=${runId}` : ''}`;
    const changed = previousQuery.current !== query;
    previousQuery.current = query;
    // 历史模式必须明确选择批次，避免日期与当前显示的数据不一致。
    if (history && runId === undefined) {
      setLoading(false);
      return () => controller.abort();
    }
    const cached = readCache<Board>(query);
    if (cached !== undefined) {
      // 命中缓存直接渲染，不转圈；后台静默刷新。
      setBoard(cached);
      setLoading(false);
      setError('');
    } else {
      setLoading(true);
      setError('');
      if (changed) setBoard({ run: null, items: [] });
    }
    get<Board>(query, controller.signal, { cache: true })
      .then(setBoard)
      .catch((e) => {
        if (!controller.signal.aborted) setError((e as Error).message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [kind, history, runId, tick]);

  return {
    kind,
    setKind,
    day,
    setDay,
    runs,
    runId,
    setRunId,
    board,
    loading,
    runsLoading,
    error,
    runError,
  };
}
