import { useEffect, useState } from 'react';
import { get } from '../../../api/http';
import { useRefreshTick } from '../../../hooks/useRefreshTick';
import type { Meta, Topic } from '../../../types/knowledge';
/** 知识列表的筛选、分页和刷新状态，视图仅负责渲染。 */
export function useKnowledgeTopics() {
  const [labels, setLabels] = useState<string[]>([]);
  const [kind, setKind] = useState<string>();
  const [region, setRegion] = useState<string>();
  const [q, setQ] = useState('');
  const [day, setDay] = useState('');
  const [page, setPage] = useState(1);
  const [pageSize, setPageSize] = useState(20);
  const [sourceId, setSourceId] = useState<number>();
  const [sortBy, setSortBy] = useState('published');
  const [data, setData] = useState<{ total: number; items: Topic[] }>({ total: 0, items: [] });
  const [meta, setMeta] = useState<Meta>({
    categories: [],
    total: 0,
    sources: [],
  });
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const { tick, refresh } = useRefreshTick();
  // 元数据（分类/标签/来源/总数）变化低频，独立慢速刷新，避免每次筛选都重拉。
  const { tick: metaTick, refresh: refreshMeta } = useRefreshTick(300_000);
  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize), q });
    labels.forEach((label) => params.append('labels', label));
    if (sourceId) params.set('source_id', String(sourceId));
    params.set('sort_by', sortBy);
    if (region) params.set('region', region);
    if (kind) params.set('topic_kind', kind);
    if (day) params.set('day', day);
    setLoading(true);
    setError('');
    get<typeof data>(`/knowledge/topics?${params}`, controller.signal)
      .then(setData)
      .catch((e) => {
        if (!controller.signal.aborted) setError((e as Error).message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [page, pageSize, sourceId, sortBy, labels, kind, region, q, day, tick]);
  useEffect(() => {
    const controller = new AbortController();
    get<Meta>('/knowledge/meta', controller.signal)
      .then(setMeta)
      .catch(() => {
        // 元数据读取失败不阻塞列表；下次周期重试。
      });
    return () => controller.abort();
  }, [metaTick]);
  return {
    labels,
    setLabels,
    kind,
    setKind,
    region,
    setRegion,
    q,
    setQ,
    day,
    setDay,
    page,
    setPage,
    pageSize,
    setPageSize,
    sourceId,
    setSourceId,
    sortBy,
    setSortBy,
    data,
    meta,
    loading,
    error,
    refresh: () => {
      refresh();
      refreshMeta();
    },
  };
}
