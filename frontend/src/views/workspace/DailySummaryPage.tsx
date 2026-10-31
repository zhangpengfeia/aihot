import { PlusOutlined } from '@ant-design/icons';
import { useEffect, useRef, useState } from 'react';
import { Alert, Button, Card, Checkbox, Empty, Modal, Space, Table, Tag, Typography } from 'antd';
import {
  DndContext,
  DragOverlay,
  MeasuringStrategy,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import { arrayMove, SortableContext, sortableKeyboardCoordinates } from '@dnd-kit/sortable';
import { useAuth } from '../../app/auth';
import { PageHeading as Heading } from '../../components/common/PageHeading';
import { useResource } from '../../hooks/useResource';
import {
  CARD_LABELS,
  dashboardScope,
  DEFAULT_LAYOUT,
  useDashboardStore,
  type CardId,
} from '../../store/dashboardStore';
import type { Snapshot } from '../../types/skills';
import type { Summary } from '../../types/workspace-responses';
import { formatTime } from '../../utils/date';
import { HotSearchCard } from './HotSearchCard';
import { FavoritesDashboardCard, KnowledgeDashboardCard } from './DashboardExtras';
import { SortableDashboardCard } from './SortableDashboardCard';
const { Text } = Typography;
export function DailySummaryPage({
  tick,
  onSelect,
}: {
  tick: number;
  onSelect: (id: number) => void;
}) {
  const { user, loading: authLoading } = useAuth();
  const scope = dashboardScope(user?.id);
  const layout = useDashboardStore((state) => state.layouts[scope] ?? DEFAULT_LAYOUT);
  const syncing = useDashboardStore((state) => state.syncing[scope] ?? false);
  const error = useDashboardStore((state) => state.errors[scope] ?? '');
  const { activate, load, setCards, setWidth, sync } = useDashboardStore.getState();
  const cards = layout.cards.filter((id) => user || id !== 'favorites');
  const [previewOrder, setPreviewOrder] = useState<CardId[] | null>(null);
  const [activeCard, setActiveCard] = useState<CardId | null>(null);
  const [editing, setEditing] = useState(false);
  const lastOver = useRef<string | null>(null);
  const displayCards = previewOrder ?? cards;
  const [draft, setDraft] = useState<CardId[]>([]);
  const [addOpen, setAddOpen] = useState(false);
  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 6 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  );
  useEffect(() => {
    setPreviewOrder(null);
    setActiveCard(null);
    setEditing(false);
    setAddOpen(false);
    if (authLoading) return;
    activate(scope);
    void load(scope);
    const retry = () => {
      void load(scope);
    };
    window.addEventListener('online', retry);
    window.addEventListener('focus', retry);
    return () => {
      window.removeEventListener('online', retry);
      window.removeEventListener('focus', retry);
    };
  }, [scope, authLoading, activate, load]);
  const resource = useResource<Summary>('/workspace/daily-summary', tick);
  const data = resource.data;
  function list(items: Snapshot[], mode: 'new' | 'rise' | 'growth') {
    return (
      <Table<Snapshot>
        rowKey="repo_id"
        size="small"
        pagination={false}
        dataSource={items}
        scroll={{ x: 460 }}
        locale={{ emptyText: <Empty description="暂无符合条件的项目" /> }}
        columns={[
          {
            title: '项目',
            render: (_, item) => (
              <Button type="link" className="project-link" onClick={() => onSelect(item.id)}>
                {item.full_name}
              </Button>
            ),
          },
          {
            title: mode === 'growth' ? '7天 净增 Star' : mode === 'rise' ? '排名变化' : '本期排名',
            width: 150,
            render: (_, item) =>
              mode === 'growth' ? (
                <Text type="success">+{item.delta_7d?.toLocaleString()}</Text>
              ) : mode === 'rise' ? (
                <Tag color="green">
                  ↑ {(item as Summary['risers'][number]).rank_change} 名 · #{item.rank}
                </Tag>
              ) : (
                <Tag>#{item.rank}</Tag>
              ),
          },
        ]}
      />
    );
  }
  function cardContent(id: CardId) {
    switch (id) {
      case 'overview':
        return (
          <Card title="项目 · 批次概览" loading={resource.loading}>
            {data?.current ? (
              <Space orientation="vertical">
                <Text>
                  本期：{formatTime(data.current.finished_at)} · 前期：
                  {formatTime(data.previous?.finished_at ?? null)}
                </Text>
                <Text type="secondary">
                  {data.previous
                    ? '新上榜指未进入前期累计 Star 榜，不代表新建仓库。'
                    : '只有一期成功榜单，暂不判断新上榜和名次变化。'}{' '}
                  7天 增长使用已有观测基线，缺失时不推算。
                </Text>
              </Space>
            ) : (
              <Empty description="暂无成功采集记录" />
            )}
          </Card>
        );
      case 'new_entries':
        return (
          <Card title={`新上榜 · ${data?.new_entries.length ?? 0}`}>
            {list(data?.new_entries ?? [], 'new')}
          </Card>
        );
      case 'risers':
        return (
          <Card title={`排名上升 · ${data?.risers.length ?? 0}`}>
            {list(data?.risers ?? [], 'rise')}
          </Card>
        );
      case 'growth':
        return (
          <Card title="7天 Star 正增长 · 前 10 个项目">{list(data?.growth ?? [], 'growth')}</Card>
        );
      case 'knowledge':
        return <KnowledgeDashboardCard tick={tick} />;
      case 'hotlists':
        return (
          <Card title="全网热搜" className="dashboard-hot-search-card">
            <HotSearchCard tick={tick} />
          </Card>
        );
      case 'favorites':
        return user ? <FavoritesDashboardCard key={user.id} tick={tick} /> : null;
    }
  }
  return (
    <>
      <Heading
        title="首页看板"
        description="自定义首页内容，拖动卡片调整顺序。"
        {...resource}
        actions={
          <>
            <Text type="secondary">
              {!user
                ? '访客 · 本地保存'
                : syncing
                  ? '同步中…'
                  : layout.dirty
                    ? '已本地保存 · 待同步'
                    : '账号配置已同步'}
            </Text>
            <Button
              type={editing ? 'primary' : 'default'}
              disabled={authLoading}
              onClick={() => setEditing((value) => !value)}
            >
              {editing ? '完成编辑' : '编辑首页卡片'}
            </Button>
          </>
        }
      />
      <Modal
        title="新增首页卡片"
        open={editing && addOpen}
        onCancel={() => setAddOpen(false)}
        okText="添加卡片"
        okButtonProps={{ disabled: !draft.length }}
        onOk={() => {
          setCards(scope, [...cards, ...draft.filter((id) => !cards.includes(id))]);
          setAddOpen(false);
        }}
      >
        <Typography.Paragraph type="secondary">
          选择要新增的卡片，添加后可拖拽排序。右上角 X 只从首页移除卡片，不删除业务数据。
        </Typography.Paragraph>
        <Checkbox.Group
          value={draft}
          onChange={(values) => setDraft(values as CardId[])}
          options={Object.entries(CARD_LABELS)
            .filter(([id]) => !cards.includes(id as CardId) && (user || id !== 'favorites'))
            .map(([value, label]) => ({ value, label }))}
        />
        {Object.keys(CARD_LABELS)
          .filter((id) => user || id !== 'favorites')
          .every((id) => cards.includes(id as CardId)) && (
          <Empty description="全部可用卡片已添加" />
        )}
      </Modal>
      <Space orientation="vertical" className="full-width" size={16}>
        {error && (
          <Alert
            type="warning"
            title="配置已保留在本地，后端同步暂未完成"
            description={error}
            action={
              <Button
                loading={syncing}
                onClick={() => {
                  void (layout.dirty ? sync(scope) : load(scope));
                }}
              >
                重试同步
              </Button>
            }
          />
        )}
        {resource.error && <Alert type="error" title={resource.error} />}
        {!displayCards.length && (
          <Empty description="此分类暂无展示卡片，可点击编辑首页卡片添加或调整筛选" />
        )}
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          measuring={{ droppable: { strategy: MeasuringStrategy.Always } }}
          onDragStart={({ active }) => {
            if (!editing) return;
            setActiveCard(active.id as CardId);
            setPreviewOrder([...cards]);
            lastOver.current = null;
          }}
          onDragOver={({ active, over, activatorEvent }) => {
            if (!editing || !over) return;
            if (active.id === over.id) {
              lastOver.current = null;
              return;
            }
            if (!(activatorEvent instanceof KeyboardEvent) && lastOver.current === String(over.id))
              return;
            lastOver.current = String(over.id);
            setPreviewOrder((previous) => {
              const order = previous ?? cards;
              const from = order.indexOf(active.id as CardId),
                to = order.indexOf(over.id as CardId);
              return from < 0 || to < 0 ? order : arrayMove(order, from, to);
            });
          }}
          onDragCancel={() => {
            setPreviewOrder(null);
            setActiveCard(null);
          }}
          onDragEnd={({ over }) => {
            if (editing && over && previewOrder) setCards(scope, previewOrder);
            setPreviewOrder(null);
            setActiveCard(null);
          }}
        >
          <SortableContext items={displayCards} strategy={() => null}>
            <div className="dashboard-sort-grid">
              {displayCards.map((id) => (
                <SortableDashboardCard
                  key={id}
                  id={id}
                  editing={editing}
                  width={layout.widths[id]}
                  onWidthChange={(value) => setWidth(scope, id, value)}
                  onRemove={() =>
                    setCards(
                      scope,
                      cards.filter((card) => card !== id),
                    )
                  }
                >
                  {cardContent(id)}
                </SortableDashboardCard>
              ))}
              {editing && (
                <Button
                  type="dashed"
                  className="dashboard-add-card"
                  size="large"
                  icon={<PlusOutlined />}
                  onClick={() => {
                    setDraft([]);
                    setAddOpen(true);
                  }}
                >
                  新增卡片
                </Button>
              )}
            </div>
          </SortableContext>
          <DragOverlay dropAnimation={null}>
            {activeCard && (
              <Card className="dashboard-drag-preview" size="small">
                <Space>
                  <strong>{CARD_LABELS[activeCard]}</strong>
                  <Tag>{layout.widths[activeCard] === 'half' ? '半行' : '整行'}</Tag>
                </Space>
              </Card>
            )}
          </DragOverlay>
        </DndContext>
      </Space>
    </>
  );
}
