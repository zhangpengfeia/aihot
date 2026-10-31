import type { HotPlatform, HotSource } from '../types/hotlists';
export function legacyPlatforms(items: HotSource[]): HotPlatform[] {
  const known: Record<string, string> = {
    百度: 'baidu',
    微博: 'weibo',
    知乎: 'zhihu',
    掘金: 'juejin',
    Readhub: 'readhub',
    小红书: 'xiaohongshu',
  };
  const grouped = new Map<string, HotPlatform>();
  for (const source of items) {
    const name = source.name.replace('热搜 · ', '').split(/[（(]/)[0].trim();
    const id = known[name] ?? `legacy:${name}`;
    const candidate: HotPlatform = {
      ...source,
      id,
      name,
      region: source.region ?? '国内',
      category: source.category ?? '综合',
      connection_status: 'configured',
      source_count: 1,
      source_name: source.name,
    };
    const previous = grouped.get(id);
    if (!previous) grouped.set(id, candidate);
    else if (
      (candidate.items.length > 0 && previous.items.length === 0) ||
      (candidate.enabled && !previous.enabled)
    )
      grouped.set(id, { ...candidate, source_count: previous.source_count + 1 });
    else grouped.set(id, { ...previous, source_count: previous.source_count + 1 });
  }
  return [...grouped.values()];
}
