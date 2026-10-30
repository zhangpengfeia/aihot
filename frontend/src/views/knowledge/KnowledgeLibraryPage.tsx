import { BulbOutlined,ReloadOutlined } from "@ant-design/icons";
import type { TableProps } from "antd";
import {
Alert,
Badge,
Button,
Card,
Col,
DatePicker,
Empty,
Flex,
Input,
Row,
Select,
Space,
Statistic,
Table,
Tag,
Typography
} from "antd";
import { useEffect,useState } from "react";
import { get } from '../../api/http';
import { AddToBoard } from "../../components/workspace/PersonalActions";
import type { Meta,Topic } from '../../types/knowledge';
import { formatTime } from '../../utils/date';
import { KnowledgeDetailDrawer } from './components/KnowledgeDetailDrawer';
const {Title,Text,Paragraph}=Typography;
export default function KnowledgePage() {
  const [category, setCategory] = useState<string>();
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
  const [selected, setSelected] = useState<Topic | null>(null);
  const [tick, setTick] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setTick((v) => v + 1), 60000);
    return () => window.clearInterval(timer);
  }, []);
  useEffect(() => {
    const controller = new AbortController();
    const params = new URLSearchParams({ page: String(page), page_size: String(pageSize), q });
    if (category) params.set('category', category);
    if (sourceId) params.set('source_id', String(sourceId));
    params.set('sort_by', sortBy);
    if (region) params.set('region', region);
    if (kind) params.set('topic_kind', kind);
    if (day) params.set('day', day);
    setLoading(true);
    setError('');
    Promise.all([
      get<typeof data>(`/knowledge/topics?${params}`, controller.signal),
      get<Meta>('/knowledge/meta', controller.signal),
    ])
      .then(([items, info]) => {
        setData(items);
        setMeta(info);
      })
      .catch((e) => {
        if (!controller.signal.aborted) setError((e as Error).message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [page, pageSize, sourceId, sortBy, category, kind, region, q, day, tick]);
  const columns: TableProps<Topic>['columns'] = [
    {
      title: '知识选题',
      key: 'topic',
      width: 440,
      render: (_, item) => (
        <div>
          <Button type="link" className="project-link" onClick={() => setSelected(item)}>
            {item.title}
          </Button>
          <Paragraph className="project-description" ellipsis={{ rows: 2 }}>
            {item.summary}
          </Paragraph>
          <Space>
            <Tag color="blue">{item.category}</Tag>
            <Tag>{item.region}</Tag>
            <Tag color={item.topic_kind === '知识探索' ? 'purple' : 'orange'}>
              {item.topic_kind}
            </Tag>
          </Space>
        </div>
      ),
    },
    {
      title: '发现渠道',
      key: 'sources',
      width: 190,
      render: (_, item) => (
        <Space orientation="vertical" size={4}>
          <Text>{item.source_name}</Text>
          {item.channels?.length > 1 && <Tag color="cyan">{item.channels.length} 个渠道收录</Tag>}
          {item.channels
            ?.filter((c) => c.score !== null)
            .map((c) => (
              <Tag key={c.name}>来源指标 {c.score}</Tag>
            ))}
        </Space>
      ),
    },
    {
      title: '发布日期',
      dataIndex: 'published_at',
      width: 180,
      render: (value: string | null) => (
        <Text type="secondary">{value ? formatTime(value) : '原来源未提供'}</Text>
      ),
    },
    {
      title: '操作',
      width: 280,
      render: (_, item) => (
        <Space wrap>
          <Button icon={<BulbOutlined />} onClick={() => setSelected(item)}>
            选题资料
          </Button>
          <AddToBoard topicId={item.id} />
        </Space>
      ),
    },
  ];
  const failed = meta.sources.filter((s) => s.enabled !== false && s.status === 'failed');
  return (
    <>
      <Flex justify="space-between" align="center" wrap gap={16} className="page-heading">
        <div>
          <Space>
            <Title level={2}>知识选题库</Title>
            <Tag color="purple">内容灵感</Tag>
          </Space>
          <Paragraph type="secondary">
            融合国内外 API、RSS 与学术资料，覆盖科技、商业、文化、教育、健康、心理、环境等题材。
          </Paragraph>
        </div>
        <Button icon={<ReloadOutlined />} loading={loading} onClick={() => setTick((v) => v + 1)}>
          刷新数据
        </Button>
      </Flex>
      <Space orientation="vertical" size={16} className="full-width">
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Card>
              <Statistic title="已收录知识选题" value={meta.total} />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card>
              <Statistic title="内容分类数量" value={meta.categories.length} />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card>
              <Statistic
                title="已运行采集来源"
                value={meta.sources.filter((s) => s.enabled !== false).length}
              />
            </Card>
          </Col>
        </Row>
        <Alert
          type="info"
          showIcon
          title="热点候选按发布日期排序，知识探索用于常青与小众题材；未接入阅读量，不能据此认定全网热门或冷门。"
        />
        {failed.length > 0 && (
          <Alert
            type="warning"
            showIcon
            title={`${failed.length} 个来源最近采集失败，其他来源与历史资料仍可用`}
            description={failed.map((s) => `${s.name}：${s.error}`).join('；')}
          />
        )}
        {meta.category_catalog && (
          <Alert
            type={meta.category_catalog.status === 'success' ? 'info' : 'warning'}
            showIcon
            title={
              meta.category_catalog.status === 'success'
                ? `远程分类目录包含 ${meta.category_catalog.remote_count} 个分类`
                : meta.category_catalog.error || '远程分类同步中，当前显示本地分类'
            }
            description={
              <>
                来源：
                <a href={meta.category_catalog.source_url} target="_blank" rel="noreferrer">
                  {meta.category_catalog.source_name}
                </a>{' '}
                · 最近同步：{formatTime(meta.category_catalog.updated_at)}。
                远程目录每日更新；筛选仅显示已有内容且未隐藏的分类。
              </>
            }
          />
        )}
        <Card size="small">
          <Flex gap={12} wrap>
            <Select
              aria-label="题材地区"
              placeholder="国内 / 国外"
              allowClear
              value={region}
              onChange={(value) => {
                setRegion(value);
                setPage(1);
              }}
              style={{ width: 150 }}
              options={[
                { label: '国内题材', value: '国内' },
                { label: '国外题材', value: '国外' },
              ]}
            />
            <Input.Search
              aria-label="搜索知识选题"
              placeholder="搜索标题或摘要"
              allowClear
              onSearch={(value) => {
                setQ(value);
                setPage(1);
              }}
              style={{ width: 280 }}
            />
            <Select
              aria-label="内容分类"
              placeholder="全部内容分类"
              showSearch
              optionFilterProp="label"
              allowClear
              value={category}
              onChange={(value) => {
                setCategory(value);
                setPage(1);
              }}
              style={{ width: 150 }}
              options={meta.categories.map((value) => ({ label: value, value }))}
            />
            <Select
              aria-label="选题类型"
              placeholder="全部选题类型"
              allowClear
              value={kind}
              onChange={(value) => {
                setKind(value);
                setPage(1);
              }}
              style={{ width: 170 }}
              options={['热点候选', '知识探索'].map((value) => ({ label: value, value }))}
            />
            <Select
              aria-label="采集接口"
              placeholder="全部采集接口"
              allowClear
              showSearch
              optionFilterProp="label"
              value={sourceId}
              onChange={(value) => {
                setSourceId(value);
                setPage(1);
              }}
              style={{ width: 220 }}
              options={meta.sources
                .filter((s) => s.id)
                .map((s) => ({ value: s.id!, label: s.name }))}
            />
            <Select
              aria-label="排序方式"
              value={sortBy}
              onChange={(value) => {
                setSortBy(value);
                setPage(1);
              }}
              style={{ width: 160 }}
              options={[
                { value: 'published', label: '按发布日期排序' },
                { value: 'collected', label: '按入库时间排序' },
              ]}
            />
            <DatePicker
              aria-label="发布日期"
              placeholder="发布日期"
              onChange={(value) => {
                setDay(value?.format('YYYY-MM-DD') ?? '');
                setPage(1);
              }}
            />
          </Flex>
        </Card>
        {error ? (
          <Alert
            type="error"
            showIcon
            title="知识资料读取失败"
            description={error}
            action={<Button onClick={() => setTick((v) => v + 1)}>重试</Button>}
          />
        ) : (
          <Card
            title={
              <Space>
                <BulbOutlined />
                知识选题<Tag>{data.total} 条</Tag>
              </Space>
            }
            className="ranking-card"
          >
            <Table<Topic>
              rowKey="id"
              columns={columns}
              dataSource={data.items}
              loading={loading}
              scroll={{ x: 900 }}
              pagination={{
                current: page,
                pageSize,
                total: data.total,
                onChange: (next, size) => {
                  setPage(size === pageSize ? next : 1);
                  setPageSize(size);
                },
                showSizeChanger: true,
                pageSizeOptions: [20, 50, 100],
                showQuickJumper: true,
                showTotal: (total, range) => `共 ${total} 条，第 ${range[0]}–${range[1]} 条`,
                position: ['topRight', 'bottomRight'],
              }}
              locale={{
                emptyText: <Empty description="暂无匹配选题，启动知识采集进程后自动入库。" />,
              }}
            />
          </Card>
        )}
        <Card title="采集来源状态" size="small">
          <Flex gap={20} wrap>
            {meta.sources.length ? (
              meta.sources.map((s) => (
                <Space key={s.name} orientation="vertical" size={3}>
                  <Badge
                    status={
                      s.enabled === false
                        ? 'default'
                        : s.status === 'success'
                          ? 'success'
                          : s.status === 'pending'
                            ? 'processing'
                            : 'error'
                    }
                    text={`${s.name}${s.enabled === false ? '（已停用）' : ''}`}
                  />
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {s.display_category ?? s.category} · 最近成功：{formatTime(s.last_success)}
                  </Text>
                </Space>
              ))
            ) : (
              <Text type="secondary">知识采集进程尚未运行，无需 GitHub Token。</Text>
            )}
          </Flex>
        </Card>
      </Space>
      <KnowledgeDetailDrawer selected={selected} onClose={()=>setSelected(null)}/>
    </>
  );
}
