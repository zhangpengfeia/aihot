import { useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Col,
  Empty,
  Flex,
  Input,
  Modal,
  Popconfirm,
  Row,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { ReloadOutlined } from '@ant-design/icons';
import {
  CREATION_STAGES,
  formatTime,
  get,
  write,
  type CreationCard,
  type PersonalItem,
  type Run,
  type Snapshot,
} from './api';
import { PersonalButton } from './PersonalActions';
const { Title, Text, Paragraph } = Typography;

function useResource<T>(path: string, tick: number) {
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

function Heading({
  title,
  description,
  refresh,
  loading,
}: {
  title: string;
  description: string;
  refresh: () => void;
  loading: boolean;
}) {
  return (
    <Flex justify="space-between" align="center" wrap gap={16} className="page-heading">
      <div>
        <Title level={2}>{title}</Title>
        <Paragraph type="secondary">{description}</Paragraph>
      </div>
      <Button icon={<ReloadOutlined />} onClick={refresh} loading={loading}>
        刷新数据
      </Button>
    </Flex>
  );
}

export function FavoritesPage({
  tick,
  onSelect,
}: {
  tick: number;
  onSelect: (id: number) => void;
}) {
  const [q, setQ] = useState('');
  const [kind, setKind] = useState<string>();
  const [scope, setScope] = useState('favorites');
  const [page, setPage] = useState(1);
  const params = new URLSearchParams({ page: String(page), q });
  if (kind) params.set('kind', kind);
  if (scope === 'notes') params.set('all_records', 'true');

  const resource = useResource<{ total: number; items: PersonalItem[] }>(
    `/workspace/items?${params}`,
    tick,
  );
  const [notice, context] = message.useMessage();
  useEffect(() => {
    if (resource.data)
      setPage((current) => Math.min(current, Math.max(1, Math.ceil(resource.data!.total / 20))));
  }, [resource.data]);
  return (
    <>
      {context}
      <Heading
        title="收藏与个人备注"
        description="整理关注的项目和知识选题，备注与收藏保存在当前实例。"
        {...resource}
      />
      <Space orientation="vertical" size={16} className="full-width">
        <Card size="small">
          <Flex wrap gap={12}>
            <Input.Search
              aria-label="搜索收藏和备注"
              allowClear
              placeholder="搜索名称或备注"
              style={{ width: 280 }}
              onSearch={(v) => {
                setQ(v);
                setPage(1);
              }}
            />
            <Select
              aria-label="资料类型"
              allowClear
              placeholder="全部类型"
              value={kind}
              style={{ width: 150 }}
              options={[
                { value: 'repository', label: 'GitHub 项目' },
                { value: 'topic', label: '知识选题' },
              ]}
              onChange={(v) => {
                setKind(v);
                setPage(1);
              }}
            />
            <Select
              aria-label="收藏范围"
              value={scope}
              style={{ width: 190 }}
              options={[
                { value: 'favorites', label: '已收藏' },
                { value: 'notes', label: '全部收藏与备注记录' },
              ]}
              onChange={(v) => {
                setScope(v);
                setPage(1);
              }}
            />
          </Flex>
        </Card>
        {resource.error && <Alert type="error" title={resource.error} showIcon />}
        <Card>
          <Table<PersonalItem>
            rowKey="id"
            loading={resource.loading}
            dataSource={resource.data?.items ?? []}
            scroll={{ x: 850 }}
            pagination={{
              current: page,
              pageSize: 20,
              total: resource.data?.total ?? 0,
              showSizeChanger: false,
              onChange: setPage,
            }}
            locale={{
              emptyText: <Empty description="暂无收藏，可从项目或选题详情添加收藏和备注。" />,
            }}
            columns={[
              {
                title: '资料',
                render: (_, item) => (
                  <Space orientation="vertical">
                    <a href={item.url} target="_blank" rel="noreferrer">
                      {item.title}
                    </a>
                    <Space>
                      <Tag>{item.target_kind === 'repository' ? 'GitHub 项目' : '知识选题'}</Tag>
                      <Tag color={item.favorite ? 'gold' : undefined}>
                        {item.favorite ? '已收藏' : '仅保留记录'}
                      </Tag>
                    </Space>
                  </Space>
                ),
              },
              {
                title: '个人备注',
                dataIndex: 'note',
                width: 300,
                render: (v: string) => (
                  <Paragraph ellipsis={{ rows: 3 }} style={{ whiteSpace: 'pre-wrap' }}>
                    {v || '暂无备注'}
                  </Paragraph>
                ),
              },
              { title: '更新时间', dataIndex: 'updated_at', width: 170, render: formatTime },
              {
                title: '操作',
                width: 250,
                render: (_, item) => (
                  <Space wrap>
                    {item.snapshot_id && (
                      <Button onClick={() => onSelect(item.snapshot_id!)}>项目资料</Button>
                    )}
                    <PersonalButton
                      kind={item.target_kind}
                      targetId={item.target_id}
                      onSaved={resource.refresh}
                    />
                    <Popconfirm
                      title="删除此收藏和备注记录？"
                      description="不会删除原始项目或选题。"
                      onConfirm={async () => {
                        try {
                          await write(
                            `/workspace/items/${item.target_kind}/${item.target_id}`,
                            'DELETE',
                          );
                          resource.refresh();
                        } catch (e) {
                          notice.error((e as Error).message);
                        }
                      }}
                    >
                      <Button danger>删除</Button>
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      </Space>
    </>
  );
}

interface Summary {
  current: Run | null;
  previous: Run | null;
  new_entries: Snapshot[];
  risers: (Snapshot & { previous_rank: number; rank_change: number })[];
  growth: Snapshot[];
}
export function DailySummaryPage({
  tick,
  onSelect,
}: {
  tick: number;
  onSelect: (id: number) => void;
}) {
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
            title: mode === 'growth' ? '24h 净增 Star' : mode === 'rise' ? '排名变化' : '本期排名',
            width: 150,
            render: (_, item) =>
              mode === 'growth' ? (
                <Text type="success">+{item.delta_24h?.toLocaleString()}</Text>
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
  return (
    <>
      <Heading
        title="每日变化摘要"
        description="对比最近两次成功的累计 Star 榜，快速查看值得关注的变化。"
        {...resource}
      />
      <Space orientation="vertical" size={16} className="full-width">
        {resource.error && <Alert type="error" showIcon title={resource.error} />}
        <Spin spinning={resource.loading}>
          <Card>
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
                  24h 增长使用已有观测基线，缺失时不推算。
                </Text>
              </Space>
            ) : (
              <Empty description="暂无成功采集记录" />
            )}
          </Card>
        </Spin>
        <Row gutter={[16, 16]}>
          <Col xs={24} xl={12}>
            <Card title={`新上榜 · ${data?.new_entries.length ?? 0}`}>
              {list(data?.new_entries ?? [], 'new')}
            </Card>
          </Col>
          <Col xs={24} xl={12}>
            <Card title={`排名上升 · ${data?.risers.length ?? 0}`}>
              {list(data?.risers ?? [], 'rise')}
            </Card>
          </Col>
        </Row>
        <Card title="24h Star 正增长 · 前 10 个项目">{list(data?.growth ?? [], 'growth')}</Card>
      </Space>
    </>
  );
}

interface Status {
  schedule: string;
  next_scheduled_at: string;
  server_time: string;
  latest: Run | null;
  last_success: Run | null;
  last_failure: Run | null;
  recent_runs: Run[];
  total_successful_runs: number;
  knowledge_sources: {
    name: string;
    status: string;
    last_attempt: string | null;
    last_success: string | null;
    error: string | null;
  }[];
}
const runLabels: Record<string, string> = {
  success: '成功',
  failed: '失败',
  running: '运行中',
  pending: '等待采集',
  disabled: '已停用',
};
export function CollectionStatusPage({ tick }: { tick: number }) {
  const resource = useResource<Status>('/workspace/collection-status', tick);
  const data = resource.data;
  return (
    <>
      <Heading
        title="采集状态面板"
        description="查看采集记录和计划时间，页面每分钟刷新。"
        {...resource}
      />
      <Space orientation="vertical" size={16} className="full-width">
        {resource.error && <Alert type="error" showIcon title={resource.error} />}
        <Alert
          type="info"
          showIcon
          title="GitHub 每天北京时间 02:00 采集；知识来源每半小时采集。"
          description="下次执行为计划时间，需要 worker 持续运行；运行中状态来自数据库记录，不能据此确认进程在线。"
        />
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={8}>
            <Card>
              <Statistic
                title="成功采集批次"
                value={data?.total_successful_runs ?? 0}
                loading={resource.loading}
              />
            </Card>
          </Col>
          <Col xs={24} lg={8}>
            <Card title="下次 GitHub 计划执行">{formatTime(data?.next_scheduled_at ?? null)}</Card>
          </Col>
          <Col xs={24} lg={8}>
            <Card title="最近成功完成">{formatTime(data?.last_success?.finished_at ?? null)}</Card>
          </Col>
        </Row>
        <Card title="最近一次尝试">
          <Text>
            {data?.latest
              ? `${formatTime(data.latest.started_at)} · ${runLabels[data.latest.status]}`
              : '尚无采集记录'}
          </Text>
          {data?.latest?.error && (
            <Alert type="error" title={data.latest.error} style={{ marginTop: 12 }} />
          )}
          {data?.last_failure && (
            <Paragraph type="secondary" style={{ marginTop: 12 }}>
              最近失败：{formatTime(data.last_failure.started_at)} ·{' '}
              {data.last_failure.error || '未记录原因'}
            </Paragraph>
          )}
        </Card>
        <Card title="GitHub 最近 10 次采集">
          <Table<Run>
            rowKey="id"
            dataSource={data?.recent_runs ?? []}
            loading={resource.loading}
            pagination={false}
            scroll={{ x: 750 }}
            columns={[
              { title: '开始时间', dataIndex: 'started_at', render: formatTime },
              { title: '完成时间', dataIndex: 'finished_at', render: formatTime },
              {
                title: '状态',
                dataIndex: 'status',
                render: (v: string) => (
                  <Tag color={v === 'success' ? 'green' : v === 'failed' ? 'red' : 'blue'}>
                    {runLabels[v]}
                  </Tag>
                ),
              },
              { title: '收录项目', dataIndex: 'matched_count' },
              { title: '失败原因', dataIndex: 'error', render: (v: string | null) => v || '—' },
            ]}
          />
        </Card>
        <Card title="知识来源状态">
          <Table
            rowKey="name"
            dataSource={data?.knowledge_sources ?? []}
            pagination={false}
            scroll={{ x: 700 }}
            columns={[
              { title: '来源', dataIndex: 'name' },
              { title: '状态', dataIndex: 'status', render: (v: string) => runLabels[v] ?? v },
              { title: '最近尝试', dataIndex: 'last_attempt', render: formatTime },
              { title: '最近成功', dataIndex: 'last_success', render: formatTime },
              { title: '失败原因', dataIndex: 'error' },
            ]}
          />
        </Card>
      </Space>
    </>
  );
}

export function CreationBoardPage({ tick }: { tick: number }) {
  const [q, setQ] = useState('');
  const resource = useResource<{ items: CreationCard[] }>(
    `/workspace/cards?q=${encodeURIComponent(q)}`,
    tick,
  );
  const [selected, setSelected] = useState<CreationCard | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, context] = message.useMessage();
  async function update(card: CreationCard, fields: Partial<CreationCard>) {
    await write(`/workspace/cards/${card.id}`, 'PATCH', fields);
    resource.refresh();
  }
  return (
    <>
      {context}
      <Heading
        title="选题创作看板"
        description="从知识选题加入卡片，按创作进度整理脚本和成品链接。"
        {...resource}
      />
      <Space orientation="vertical" size={16} className="full-width">
        <Input.Search
          aria-label="搜索创作卡片"
          placeholder="搜索选题标题"
          allowClear
          onSearch={setQ}
          style={{ maxWidth: 360 }}
        />
        {resource.error && <Alert type="error" showIcon title={resource.error} />}
        {!resource.loading && resource.data?.items.length === 0 && (
          <Alert type="info" showIcon title="暂无创作卡片，请在知识选题库点击“加入创作看板”。" />
        )}
        <Spin spinning={resource.loading}>
          <div className="creation-board">
            {CREATION_STAGES.map((stage, index) => {
              const items = (resource.data?.items ?? []).filter((card) => card.stage === stage);
              return (
                <section key={stage} className={`creation-column creation-column-${index}`}>
                  <Flex justify="space-between" className="creation-column-heading">
                    <Text strong>{stage}</Text>
                    <Tag>{items.length}</Tag>
                  </Flex>
                  <Space orientation="vertical" size={12} className="full-width">
                    {items.map((card) => (
                      <Card key={card.id} size="small">
                        <Space orientation="vertical" className="full-width" size={12}>
                          <Text strong>{card.title}</Text>
                          <Tag>{card.category}</Tag>
                          <Paragraph
                            type="secondary"
                            ellipsis={{ rows: 3 }}
                            style={{ whiteSpace: 'pre-wrap', margin: 0 }}
                          >
                            {card.script || '还没有脚本，点击编辑开始整理。'}
                          </Paragraph>
                          {card.output_url && (
                            <a href={card.output_url} target="_blank" rel="noreferrer">
                              查看成品
                            </a>
                          )}
                          <Select
                            aria-label={`调整阶段：${card.title}`}
                            value={card.stage}
                            className="full-width"
                            options={CREATION_STAGES.map((value) => ({ value, label: value }))}
                            onChange={async (value) => {
                              try {
                                await update(card, { stage: value });
                              } catch (e) {
                                notice.error((e as Error).message);
                              }
                            }}
                          />
                          <Flex justify="space-between">
                            <Button
                              onClick={() => {
                                setSelected({ ...card });
                                setError('');
                              }}
                            >
                              编辑脚本
                            </Button>
                            <Popconfirm
                              title="删除这张创作卡片？"
                              description="不会删除原始选题。"
                              onConfirm={async () => {
                                try {
                                  await write(`/workspace/cards/${card.id}`, 'DELETE');
                                  resource.refresh();
                                } catch (e) {
                                  notice.error((e as Error).message);
                                }
                              }}
                            >
                              <Button danger type="text">
                                删除
                              </Button>
                            </Popconfirm>
                          </Flex>
                        </Space>
                      </Card>
                    ))}
                    {!items.length && <Text type="secondary">暂无选题</Text>}
                  </Space>
                </section>
              );
            })}
          </div>
        </Spin>
      </Space>
      <Modal
        title="编辑创作卡片"
        open={selected !== null}
        width={800}
        onCancel={() => setSelected(null)}
        okText="保存"
        cancelText="取消"
        confirmLoading={busy}
        onOk={async () => {
          if (!selected) return;
          setBusy(true);
          setError('');
          try {
            await update(selected, {
              stage: selected.stage,
              script: selected.script,
              output_url: selected.output_url,
            });
            setSelected(null);
            notice.success('创作卡片已保存');
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {selected && (
          <Space orientation="vertical" className="full-width" size={16}>
            {error && <Alert type="error" showIcon title={error} />}
            <Text strong>{selected.title}</Text>
            <a href={selected.source_url} target="_blank" rel="noreferrer">
              阅读原始资料
            </a>
            <Select
              aria-label="创作阶段"
              value={selected.stage}
              options={CREATION_STAGES.map((value) => ({ value, label: value }))}
              onChange={(stage) => setSelected({ ...selected, stage })}
            />
            <label htmlFor="creation-script">脚本</label>
            <Input.TextArea
              id="creation-script"
              value={selected.script}
              rows={12}
              maxLength={100000}
              showCount
              placeholder="整理开场、素材、解说与结尾……"
              onChange={(e) => setSelected({ ...selected, script: e.target.value })}
            />
            <label htmlFor="creation-output">成品链接</label>
            <Input
              id="creation-output"
              value={selected.output_url}
              maxLength={2000}
              placeholder="https://..."
              onChange={(e) => setSelected({ ...selected, output_url: e.target.value })}
            />
          </Space>
        )}
      </Modal>
    </>
  );
}
