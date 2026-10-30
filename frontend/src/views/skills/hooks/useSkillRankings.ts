import { useEffect,useState } from 'react';
import { get } from '../../../api/http';
import type { Board,Run } from '../../../types/skills';
export function useSkillRankings(history:boolean,tick:number){
  const [kind, setKind] = useState<'stars' | 'growth'>('stars');
  const [day, setDay] = useState('');
  const [runs, setRuns] = useState<Run[]>([]);
  const [runId, setRunId] = useState<number | undefined>();
  const [board, setBoard] = useState<Board>({ run: null, items: [] });

const [loading,setLoading]=useState(true);const [error,setError]=useState('');const [runError,setRunError]=useState('');
  useEffect(() => {
    const controller = new AbortController();
    setRunError('');
    get<Run[]>(`/runs?limit=100${history && day ? `&day=${day}` : ''}`, controller.signal)
      .then(setRuns)
      .catch((e) => {
        if (!controller.signal.aborted) setRunError((e as Error).message);
      });
    return () => controller.abort();
  }, [day, tick, history]);

  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    setBoard({ run: null, items: [] });
    // 历史模式必须明确选择批次，避免日期与当前显示的数据不一致。
    if (history && runId === undefined) {
      setLoading(false);
      return () => controller.abort();
    }
    get<Board>(`/rankings?kind=${kind}${history ? `&run_id=${runId}` : ''}`, controller.signal)
      .then(setBoard)
      .catch((e) => {
        if (!controller.signal.aborted) setError((e as Error).message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [kind, history, runId, tick]);

return {kind,setKind,day,setDay,runs,runId,setRunId,board,loading,error,runError};
}
