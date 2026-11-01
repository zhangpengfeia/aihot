import { useEffect, useRef, useState } from 'react';
import { get } from '../../../api/http';
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
    setRunsLoading(true);
    setRunError('');
    get<Run[]>(`/runs?limit=100${history && day ? `&day=${day}` : ''}`, controller.signal)
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
    // 同一榜单后台更新时保留内容，切换排名或历史批次才清空。
    setLoading(true);
    setError('');
    if (changed) setBoard({ run: null, items: [] });
    // 历史模式必须明确选择批次，避免日期与当前显示的数据不一致。
    if (history && runId === undefined) {
      setLoading(false);
      return () => controller.abort();
    }
    get<Board>(query, controller.signal)
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
