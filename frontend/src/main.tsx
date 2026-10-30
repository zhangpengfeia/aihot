import { StrictMode, useEffect, useState } from 'react';
import { createRoot } from 'react-dom/client';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  ConfigProvider,
  DatePicker,
  Descriptions,
  Drawer,
  Empty,
  Flex,
  Grid,
  Layout,
  Menu,
  Row,
  Segmented,
  Select,
  Space,
  Spin,
  Statistic,
  Table,
  Tag,
  theme,
  Typography,
  Tooltip,
} from 'antd';
import type { TableProps } from 'antd';
import zhCN from 'antd/locale/zh_CN';
import {
  ApiOutlined,
  ArrowUpOutlined,
  BookOutlined,
  BulbOutlined,
  ClockCircleOutlined,
  DownloadOutlined,
  FireOutlined,
  GithubOutlined,
  HistoryOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
  ReloadOutlined,
  StarOutlined,
} from '@ant-design/icons';
import { get, formatTime, type Board, type Run, type Snapshot } from './api';
import 'antd/dist/reset.css';
import './style.css';
import KnowledgePage from './KnowledgePage';
import SkillLibrary from './SkillLibrary';
import { PersonalButton } from './PersonalActions';
import { SourceManagementPage, CategoryManagementPage } from './KnowledgeManagementPages';
import {
  FavoritesPage,
  DailySummaryPage,
  CollectionStatusPage,
  CreationBoardPage,
} from './WorkspacePages';

const { Header, Sider, Content } = Layout;
const { Title, Text, Paragraph } = Typography;
const statusLabels = { success: '采集完成', failed: '采集失败', running: '正在采集' };
const statusColors = { success: 'success', failed: 'error', running: 'processing' } as const;

function App() {
  const screens = Grid.useBreakpoint();
  // 默认跟随屏幕宽度；用户手动操作后，保留本次页面会话的选择。
  const [menuCollapsed, setMenuCollapsed] = useState<boolean | null>(null);
  const collapsed = menuCollapsed ?? !screens.lg;
  const [kind, setKind] = useState<'stars' | 'growth'>('stars');
  const [view, setView] = useState<
    | 'library'
    | 'today'
    | 'history'
    | 'knowledge'
    | 'favorites'
    | 'summary'
    | 'status'
    | 'creation'
    | 'sources'
    | 'categories'
  >('library');
  const history = view === 'history';
  const [day, setDay] = useState('');
  const [runs, setRuns] = useState<Run[]>([]);
  const [runId, setRunId] = useState<number | undefined>();
  const [board, setBoard] = useState<Board>({ run: null, items: [] });
  const [detail, setDetail] = useState<Snapshot | null>(null);
  const [selected, setSelected] = useState<number | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [detailError, setDetailError] = useState('');
  const [tick, setTick] = useState(0);
  const [runError, setRunError] = useState('');

  // 页面轮询只读取数据库，不会触发 GitHub 采集；采集由独立 worker 调度。
  useEffect(() => {
    const timer = window.setInterval(() => setTick((v) => v + 1), 60_000);
    return () => window.clearInterval(timer);
  }, []);

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
    if (view !== 'today' && view !== 'history') {
      setLoading(false);
      return () => controller.abort();
    }
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
  }, [kind, history, runId, tick, view]);

  useEffect(() => {
    setDetail(null);
    setDetailError('');
    if (selected === null) return;
    const controller = new AbortController();
    get<Snapshot>(`/snapshots/${selected}`, controller.signal)
      .then(setDetail)
      .catch((e) => {
        if (!controller.signal.aborted) setDetailError((e as Error).message);
      });
    return () => controller.abort();
  }, [selected]);

  const latestRun = runs[0];
  const stale =
    board.run &&
    Date.now() - new Date(board.run.finished_at ?? board.run.slot).getTime() > 26 * 60 * 60_000;
  const columns: TableProps<Snapshot>['columns'] = [
    {
      title: '排名',
      dataIndex: 'rank',
      width: 76,
      render: (rank: number) => (
        <span className={`rank-badge ${rank <= 3 ? `rank-${rank}` : ''}`}>{rank}</span>
      ),
    },
    {
      title: '项目',
      key: 'project',
      width: 480,
      render: (_, item) => (
        <div className="project-cell">
          <Button type="link" className="project-link" onClick={() => setSelected(item.id)}>
            {item.full_name}
          </Button>
          <Paragraph
            className="project-description"
            ellipsis={{ rows: 2, tooltip: item.description }}
          >
            {item.description || '暂无简介，查看 README 了解详情。'}
          </Paragraph>
          <Space size={[5, 5]} wrap>
            <Tag variant="filled">{item.language || '未标注语言'}</Tag>
            <Tag variant="filled">{item.license || '未声明许可证'}</Tag>
            <Tag color="blue" variant="filled">
              Skills 规则匹配
            </Tag>
            {item.categories?.map((category) => (
              <Tag color="geekblue" key={category}>
                {category}
              </Tag>
            ))}
          </Space>
        </div>
      ),
    },
    {
      title: (
        <Space size={5}>
          <StarOutlined />
          累计 Star
        </Space>
      ),
      dataIndex: 'stars',
      width: 140,
      align: 'right',
      render: (value: number) => (
        <Text strong className="numeric">
          {value.toLocaleString()}
        </Text>
      ),
    },
    {
      title: '24h 净增长',
      dataIndex: 'delta_24h',
      width: 145,
      align: 'right',
      render: (value: number | null) =>
        value === null ? (
          <Text type="secondary">数据积累中</Text>
        ) : (
          <Text
            className="numeric"
            type={value > 0 ? 'success' : value < 0 ? 'danger' : 'secondary'}
          >
            {value > 0 && <ArrowUpOutlined />} {value.toLocaleString()}
          </Text>
        ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      align: 'center',
      fixed: screens.md ? 'right' : undefined,
      render: (_, item) => (
        <Button icon={<BookOutlined />} onClick={() => setSelected(item.id)}>
          资料
        </Button>
      ),
    },
  ];

  const empty = (
    <Empty
      image={Empty.PRESENTED_IMAGE_SIMPLE}
      description={
        <Space orientation="vertical" size={4}>
          <Text strong>
            {history && runId === undefined
              ? '请选择历史采集批次'
              : kind === 'growth' && board.run
                ? '正在积累增长数据'
                : '暂无热点数据'}
          </Text>
          <Text type="secondary">
            {history && runId === undefined
              ? '按日期查找，回看当时的榜单与原始资料。'
              : kind === 'growth' && board.run
                ? '需要至少 24 小时观测，当前可先查看累计 Star 榜。'
                : '配置数据库和 GitHub Token 后，启动采集进程。'}
          </Text>
        </Space>
      }
    />
  );

  return (
    <Layout className="app-layout">
      <Sider
        width={224}
        collapsedWidth={72}
        collapsed={collapsed}
        className="app-sider"
        theme="dark"
      >
        <div className="brand">
          <div className="brand-icon">
            <FireOutlined />
          </div>
          {!collapsed && (
            <div>
              <strong>AIHot</strong>
              <span>Skills 热点资料库</span>
            </div>
          )}
        </div>
        {!collapsed && <div className="nav-label">工作空间</div>}
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[view]}
          defaultOpenKeys={['skills', 'knowledge-group']}
          items={[
            {
              key: 'skills',
              icon: <BookOutlined />,
              label: 'Skill 库',
              children: [
                { key: 'library', label: '项目资料' },
                { key: 'today', label: '今日热榜' },
                { key: 'history', label: '历史热榜' },
              ],
            },
            {
              key: 'knowledge-group',
              icon: <BulbOutlined />,
              label: '知识选',
              children: [
                { key: 'knowledge', label: '知识选题库' },
                { key: 'sources', label: '采集接口管理' },
              ],
            },
            { key: 'favorites', icon: <StarOutlined />, label: '收藏与个人备注' },
            { key: 'summary', icon: <FireOutlined />, label: '每日变化摘要' },
            { key: 'status', icon: <ClockCircleOutlined />, label: '采集状态面板' },
            { key: 'creation', icon: <BulbOutlined />, label: '选题创作看板' },
          ]}
          onClick={({ key }) => {
            setView(key as typeof view);
            setRunId(undefined);
          }}
        />
        <div className="sider-footer">
          {!collapsed ? (
            <>
              <Badge status="processing" text={<Text>GitHub 每天 02:00 采集</Text>} />
              <p>GitHub 官方 API · 北京时间</p>
            </>
          ) : (
            <ClockCircleOutlined />
          )}
        </div>
        <Tooltip title={collapsed ? '展开菜单' : '收起菜单'} placement="right">
          <Button
            type="text"
            className="sider-toggle"
            aria-label={collapsed ? '展开菜单' : '收起菜单'}
            aria-expanded={!collapsed}
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setMenuCollapsed(!collapsed)}
          >
            {!collapsed && '收起菜单'}
          </Button>
        </Tooltip>
      </Sider>
      <Layout className={!collapsed ? 'main-layout' : 'main-layout collapsed'}>
        <Header className="app-header">
          <Space>
            <GithubOutlined />
            <Text type="secondary">创作资料库</Text>
            <Text type="secondary">/</Text>
            <Text>
              {view === 'sources'
                ? '知识选 / 采集接口管理'
                : view === 'categories'
                  ? '分类整理'
                  : view === 'favorites'
                    ? '收藏与个人备注'
                    : view === 'summary'
                      ? '每日变化摘要'
                      : view === 'status'
                        ? '采集状态面板'
                        : view === 'creation'
                          ? '选题创作看板'
                          : view === 'knowledge'
                            ? '知识选 / 知识选题库'
                            : history
                              ? 'Skill 库 / 历史热榜'
                              : view === 'library'
                                ? 'Skill 库 / 项目资料'
                                : 'Skill 库 / 今日热榜'}
            </Text>
          </Space>
          <Button icon={<ApiOutlined />} href="/docs" target="_blank">
            {screens.sm ? 'API 文档' : 'API'}
          </Button>
        </Header>
        <Content className="app-content">
          {view === 'sources' ? (
            <SourceManagementPage tick={tick} />
          ) : view === 'categories' ? (
            <CategoryManagementPage tick={tick} />
          ) : view === 'favorites' ? (
            <FavoritesPage tick={tick} onSelect={setSelected} />
          ) : view === 'summary' ? (
            <DailySummaryPage tick={tick} onSelect={setSelected} />
          ) : view === 'status' ? (
            <CollectionStatusPage tick={tick} />
          ) : view === 'creation' ? (
            <CreationBoardPage tick={tick} />
          ) : view === 'knowledge' ? (
            <KnowledgePage />
          ) : (
            <>
              <Flex className="page-heading" justify="space-between" align="center" gap={16} wrap>
                <div>
                  <Space size={8}>
                    <Title level={2}>
                      {view === 'library'
                        ? 'Skill 库'
                        : history
                          ? '历史热榜'
                          : 'GitHub Skills 热榜'}
                    </Title>
                    <Tag color="blue">{view === 'library' ? '创作工具' : 'TOP 20'}</Tag>
                  </Space>
                  <Paragraph type="secondary">
                    {view === 'library'
                      ? '按脚本写作、配音、字幕、动画、剪辑等用途整理热门项目，记录安装方式与许可证。'
                      : history
                        ? '按日期与采集批次回看，保留每次观测的热度和原始资料。'
                        : '发现值得关注的 Agent Skills，整理下一条视频的选题与资料。'}
                  </Paragraph>
                </div>
                <Button
                  icon={<ReloadOutlined spin={loading} />}
                  onClick={() => setTick((v) => v + 1)}
                  loading={loading}
                >
                  刷新数据
                </Button>
              </Flex>
              {view === 'library' ? (
                <SkillLibrary onSelect={setSelected} tick={tick} />
              ) : (
                <Space orientation="vertical" size={16} className="full-width">
                  {runError && (
                    <Alert
                      type="warning"
                      showIcon
                      title="采集状态暂时不可用"
                      description={runError}
                    />
                  )}
                  {!history && latestRun?.status === 'failed' && (
                    <Alert
                      type="warning"
                      showIcon
                      title="最近一轮采集失败，已保留上一期榜单"
                      description={latestRun.error}
                    />
                  )}
                  {!history && latestRun?.status === 'running' && (
                    <Alert type="info" showIcon title="新一轮采集中，完成后将自动更新榜单" />
                  )}
                  {!history && stale && (
                    <Alert
                      type="warning"
                      showIcon
                      title="榜单已超过 26 小时未更新，请检查采集状态"
                    />
                  )}
                  <Row gutter={[16, 16]}>
                    <Col xs={24} md={8}>
                      <Card>
                        <Statistic
                          title="本期收录 Skills"
                          value={board.run?.matched_count ?? '—'}
                          suffix={board.run ? '个' : ''}
                          prefix={<BookOutlined className="stat-icon" />}
                        />
                        <Text type="secondary" className="stat-caption">
                          符合 Skills 识别规则的项目
                        </Text>
                      </Card>
                    </Col>
                    <Col xs={24} md={8}>
                      <Card>
                        <Statistic
                          title="本期候选仓库"
                          value={board.run?.candidate_count ?? '—'}
                          suffix={board.run ? '个' : ''}
                          prefix={<GithubOutlined className="stat-icon" />}
                        />
                        <Text type="secondary" className="stat-caption">
                          搜索发现与已跟踪项目去重
                        </Text>
                      </Card>
                    </Col>
                    <Col xs={24} md={8}>
                      <Card>
                        <div className="update-label">榜单更新时间</div>
                        <div className="update-time">
                          {formatTime(board.run?.finished_at ?? null)}
                        </div>
                        <Badge
                          status={board.run ? 'success' : 'default'}
                          text={board.run ? '已完成观测 · 北京时间' : '等待采集完成'}
                        />
                      </Card>
                    </Col>
                  </Row>
                  {history && (
                    <Card
                      title={
                        <Space>
                          <HistoryOutlined />
                          历史查询
                        </Space>
                      }
                      size="small"
                    >
                      <Flex gap={16} align="end" wrap>
                        <div className="filter-field">
                          <Text>查询日期</Text>
                          <DatePicker
                            aria-label="查询日期"
                            placeholder="选择日期（北京时间）"
                            onChange={(value) => {
                              setDay(value?.format('YYYY-MM-DD') ?? '');
                              setRunId(undefined);
                            }}
                          />
                        </div>
                        <div className="filter-field batch-filter">
                          <Text>历史采集批次</Text>
                          <Select
                            aria-label="历史采集批次"
                            placeholder="请选择已完成批次"
                            value={runId}
                            onChange={setRunId}
                            allowClear
                            options={runs.map((r) => ({
                              value: r.id,
                              disabled: r.status !== 'success',
                              label: `${formatTime(r.slot)} · ${statusLabels[r.status]}`,
                            }))}
                          />
                        </div>
                        <Text type="secondary" className="filter-help">
                          未选日期显示最近 100 批，按日期可查更早记录。
                        </Text>
                      </Flex>
                    </Card>
                  )}
                  <Card
                    className="ranking-card"
                    title={
                      <Space>
                        <FireOutlined />
                        <span>{history ? '历史榜单' : '热门项目'}</span>
                        <Tag>{board.items.length} 个项目</Tag>
                      </Space>
                    }
                    extra={
                      <Segmented
                        aria-label="排名方式"
                        value={kind}
                        onChange={(value) => setKind(value as 'stars' | 'growth')}
                        options={[
                          { label: '累计 Star', value: 'stars' },
                          { label: '24h 增长', value: 'growth' },
                        ]}
                      />
                    }
                  >
                    <div className="board-note">
                      <Text type="secondary">
                        已采集候选范围内排名 · 排除 Fork 与归档仓库 · 点击项目查看资料
                      </Text>
                    </div>
                    {kind === 'growth' && (
                      <Alert
                        className="table-alert"
                        type="info"
                        showIcon
                        title="增长基线取约 24–26 小时前的观测；缺少基线的项目不参与此榜单。"
                      />
                    )}
                    {error ? (
                      <Alert
                        type="error"
                        showIcon
                        title="榜单读取失败"
                        description={error}
                        action={<Button onClick={() => setTick((v) => v + 1)}>重试</Button>}
                      />
                    ) : (
                      <Table<Snapshot>
                        columns={columns}
                        dataSource={board.items}
                        rowKey="id"
                        loading={loading}
                        pagination={false}
                        scroll={{ x: 960 }}
                        locale={{ emptyText: empty }}
                      />
                    )}
                  </Card>
                  {latestRun && !history && (
                    <Text type="secondary" className="collection-status">
                      <Badge status={statusColors[latestRun.status]} />
                      最近任务：{formatTime(latestRun.slot)} · {statusLabels[latestRun.status]}
                    </Text>
                  )}
                </Space>
              )}
              <div className="page-footer">
                数据来源：GitHub 官方 API · Skills 为规则识别，请核实原始资料 · README
                为作者原文，未经实测
              </div>
            </>
          )}
        </Content>
      </Layout>
      <Drawer
        title={
          <Space>
            <BookOutlined />
            项目资料快照
          </Space>
        }
        open={selected !== null}
        onClose={() => setSelected(null)}
        size={screens.md ? 780 : '100%'}
      >
        {detailError ? (
          <Alert type="error" showIcon title={detailError} />
        ) : !detail ? (
          <div className="drawer-loading">
            <Spin tip="读取资料中…">
              <div style={{ height: 100 }} />
            </Spin>
          </div>
        ) : (
          <Space orientation="vertical" size={24} className="full-width">
            <div>
              <Title level={3} className="detail-title">
                {detail.full_name}
              </Title>
              <Paragraph type="secondary">{detail.description || '仓库暂无简介'}</Paragraph>
              <Space wrap>
                <PersonalButton kind="repository" targetId={detail.repo_id} />
                <Button type="primary" icon={<GithubOutlined />} href={detail.url} target="_blank">
                  原始仓库
                </Button>
                <Button icon={<DownloadOutlined />} href={`/api/snapshots/${detail.id}/markdown`}>
                  下载 Markdown
                </Button>
              </Space>
            </div>
            <Descriptions
              title="观测信息"
              column={1}
              size="small"
              bordered
              items={[
                { key: 'observed', label: '观测时间', children: formatTime(detail.observed_at) },
                { key: 'stars', label: '累计 Star', children: detail.stars.toLocaleString() },
                {
                  key: 'growth',
                  label: '24h 净增长',
                  children:
                    detail.delta_24h === null ? '数据积累中' : detail.delta_24h.toLocaleString(),
                },
                { key: 'baseline', label: '增长基线', children: formatTime(detail.baseline_at) },
                { key: 'evidence', label: '识别依据', children: detail.evidence },
                { key: 'pushed', label: '最近推送', children: formatTime(detail.pushed_at) },
                { key: 'forks', label: 'Fork 数', children: detail.forks.toLocaleString() },
                { key: 'license', label: '许可证', children: detail.license || '未声明' },
                {
                  key: 'categories',
                  label: '用途分类',
                  children: detail.categories?.join('、') || '其他',
                },
              ]}
            />
            <div>
              <Title level={5}>安装方式（原文摘录）</Title>
              <Text type="secondary">以下仅记录原项目说明，未经执行验证。</Text>
              <pre className="readme-content">{detail.installation || '请查看原始仓库文档。'}</pre>
            </div>
            <div>
              <Title level={5}>README 原始资料</Title>
              <Alert
                type="info"
                showIcon
                title="以下内容由项目作者提供，未经实测。保留采集时原文，最多 100,000 字符。"
              />
              <pre className="readme-content">{detail.readme || '该仓库暂无可读取的 README。'}</pre>
            </div>
          </Space>
        )}
      </Drawer>
    </Layout>
  );
}

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <ConfigProvider
      locale={zhCN}
      theme={{
        algorithm: theme.defaultAlgorithm,
        token: {
          colorPrimary: '#2563eb',
          colorBgLayout: '#f5f7fb',
          borderRadius: 8,
          fontFamily:
            'Inter, -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", sans-serif',
        },
        components: {
          Layout: { siderBg: '#101b30', headerBg: '#fff' },
          Menu: {
            darkItemBg: '#101b30',
            darkItemSelectedBg: '#2563eb',
            darkItemHoverBg: '#1d2c46',
          },
          Table: { headerBg: '#f8fafc', cellPaddingBlock: 20 },
        },
      }}
    >
      <App />
    </ConfigProvider>
  </StrictMode>,
);
