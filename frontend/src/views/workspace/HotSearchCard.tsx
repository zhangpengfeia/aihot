import { useState } from 'react';
import { Alert, Empty, Spin, Tooltip } from 'antd';
import { StarFilled, StarOutlined } from '@ant-design/icons';
import { useAuth } from '../../app/auth';
import { useResource } from '../../hooks/useResource';
import { dashboardScope } from '../../store/dashboardStore';
import { DEFAULT_HOT_SUBSCRIPTIONS, useHotSearchCardStore } from '../../store/hotSearchCardStore';
import type { HotPlatform, HotSource } from '../../types/hotlists';
import { legacyPlatforms } from '../../utils/hotlists';
import { formatTime } from '../../utils/date';
import { PlatformPicker } from '../knowledge/components/PlatformPicker';

const COLORS: Record<string, string> = {
  baidu: '#3567ff',
  weibo: '#ff8a32',
  xiaohongshu: '#ff2748',
  zhihu: '#0084ff',
  juejin: '#1685ff',
};
function PlatformIcon({ platform }: { platform: HotPlatform }) {
  return (
    <span
      className="home-hot-icon"
      style={{ background: COLORS[platform.id] ?? '#60789d' }}
      aria-hidden="true"
    >
      {platform.name.slice(0, 1)}
    </span>
  );
}
export function HotSearchCard({ tick }: { tick: number }) {
  const resource = useResource<{ items: HotSource[]; platforms?: HotPlatform[] }>(
    '/knowledge/hotlists',
    tick,
    { silentRefresh: true, cache: true },
  );
  const { user } = useAuth();
  const scope = dashboardScope(user?.id);
  const subscribed = useHotSearchCardStore(
    (state) => state.subscriptions[scope] ?? DEFAULT_HOT_SUBSCRIPTIONS,
  );
  const save = useHotSearchCardStore((state) => state.save);
  const [group, setGroup] = useState('我的订阅');
  const [platformIds, setPlatformIds] = useState<string[]>([]);
  const [active, setActive] = useState<string | null>(null);
  const sources = resource.data?.platforms ?? legacyPlatforms(resource.data?.items ?? []);
  const groups = ['我的订阅', '全部', ...new Set(sources.map((source) => source.category))];
  const visible = sources.filter(
    (source) =>
      (!platformIds.length || platformIds.includes(source.id)) &&
      (group === '全部' ||
        (group === '我的订阅' ? subscribed.includes(source.id) : source.category === group)),
  );
  const selected =
    visible.find((source) => source.id === active) ??
    visible.find((source) => source.id === 'baidu') ??
    visible[0];
  return (
    <div className="home-hot-widget" aria-label="首页热搜卡片">
      <div className="home-hot-filters">
        <div className="home-hot-tabs" aria-label="热搜卡片分类">
          {groups.map((name) => (
            <button
              key={name}
              className={name === group ? 'is-active' : ''}
              onClick={() => {
                setGroup(name);
                setActive(null);
              }}
            >
              {name}
            </button>
          ))}
        </div>
        <PlatformPicker
          platforms={sources}
          value={platformIds}
          onChange={(ids) => {
            setPlatformIds(ids);
            setGroup('全部');
            setActive(null);
          }}
        />
      </div>
      {resource.error && <Alert type="error" title={resource.error} />}
      <Spin
        spinning={resource.loading}
        tip={resource.data ? '正在刷新热搜榜单…' : '正在加载热搜榜单…'}
      >
        <div
          className="home-hot-workspace"
          style={{ minHeight: resource.loading && !resource.data ? 240 : undefined }}
        >
          <aside className="home-hot-sidebar" aria-label="卡片内热搜平台">
            {visible.map((source) => (
              <button
                className={source.id === selected?.id ? 'is-active' : ''}
                key={source.id}
                onClick={() => setActive(source.id)}
              >
                <PlatformIcon platform={source} />
                <span>{source.name}</span>
              </button>
            ))}
            {!visible.length && (
              <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description="暂无匹配平台" />
            )}
          </aside>
          <section className="home-hot-board" aria-label="卡片内平台榜单">
            {selected ? (
              <>
                <header>
                  <PlatformIcon platform={selected} />
                  <strong>
                    {selected.name}
                    <span>
                      {' '}
                      · {selected.connection_status === 'reserved' ? '预留平台' : '实时热点'}
                    </span>
                  </strong>
                  <Tooltip title={subscribed.includes(selected.id) ? '取消订阅' : '订阅平台'}>
                    <button
                      aria-label={`${subscribed.includes(selected.id) ? '取消订阅' : '订阅'}${selected.name}`}
                      onClick={() =>
                        save(
                          scope,
                          subscribed.includes(selected.id)
                            ? subscribed.filter((id) => id !== selected.id)
                            : [...subscribed, selected.id],
                        )
                      }
                    >
                      {subscribed.includes(selected.id) ? <StarFilled /> : <StarOutlined />}
                    </button>
                  </Tooltip>
                </header>
                <div className="home-hot-meta">
                  {selected.region} ·{' '}
                  {selected.observed_at
                    ? formatTime(selected.observed_at)
                    : selected.connection_status === 'reserved'
                      ? '暂未接入 API'
                      : '等待采集'}
                </div>
                <div className="home-hot-rows">
                  {selected.error && (
                    <div className="home-hot-error">
                      最近采集失败，以下可能是历史记录：{selected.error}
                    </div>
                  )}
                  {!selected.items.length && (
                    <Empty
                      image={Empty.PRESENTED_IMAGE_SIMPLE}
                      description={
                        selected.connection_status === 'reserved'
                          ? '平台已预留，暂未接入接口'
                          : '暂无已采集榜单'
                      }
                    />
                  )}
                  {selected.items.map((item) => (
                    <a
                      className="home-hot-row"
                      key={`${item.id}-${item.rank}`}
                      href={item.source_url}
                      target="_blank"
                      rel="noreferrer"
                    >
                      <span className={`home-hot-rank rank-${item.rank}`}>{item.rank}</span>
                      <span className="home-hot-title">{item.title}</span>
                      <span className="home-hot-score">
                        {item.score_label ?? item.score?.toLocaleString() ?? '—'}
                      </span>
                    </a>
                  ))}
                </div>
              </>
            ) : (
              <Empty
                description={resource.loading ? '正在加载平台…' : '没有匹配的平台，请调整筛选'}
              />
            )}
          </section>
        </div>
      </Spin>
    </div>
  );
}
