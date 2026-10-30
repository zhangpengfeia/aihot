import {
  BookOutlined,
  FireOutlined,
  GithubOutlined,
  HistoryOutlined,
  ReloadOutlined,
} from '@ant-design/icons';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  DatePicker,
  Empty,
  Flex,
  Row,
  Segmented,
  Select,
  Space,
  Statistic,
  Tag,
  Typography,
} from 'antd';
import { formatTime } from '../../utils/date';
import { RankingTable } from './components/RankingTable';
import { useSkillRankings } from './hooks/useSkillRankings';
const { Title, Text, Paragraph } = Typography;
const statusLabels = { success: '采集完成', failed: '采集失败', running: '正在采集' };
const statusColors = { success: 'success', failed: 'error', running: 'processing' } as const;
export function SkillRankingPage({
  history,
  tick,
  onRefresh,
  onSelect,
}: {
  history: boolean;
  tick: number;
  onRefresh: () => void;
  onSelect: (id: number) => void;
}) {
  const { kind, setKind, setDay, runs, runId, setRunId, board, loading, error, runError } =
    useSkillRankings(history, tick);
  const latestRun = runs[0];
  const stale =
    board.run &&
    Date.now() - new Date(board.run.finished_at ?? board.run.slot).getTime() > 26 * 60 * 60_000;
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
    <>
      <Flex className="page-heading" justify="space-between" align="center" gap={16} wrap>
        <div>
          <Space>
            <Title level={2}>{history ? '历史热榜' : 'GitHub Skills 热榜'}</Title>
            <Tag color="blue">TOP 20</Tag>
          </Space>
          <Paragraph type="secondary">
            {history
              ? '按日期与批次查看历史榜单与原始资料。'
              : '发现值得关注的 Agent Skills，整理下一条视频的选题与资料。'}
          </Paragraph>
        </div>
        <Flex align="center" justify="flex-end" gap={12} wrap>
          {latestRun && !history && (
            <Text type="secondary" className="collection-status">
              <Badge status={statusColors[latestRun.status]} />
              最近任务：{formatTime(latestRun.slot)} · {statusLabels[latestRun.status]}
            </Text>
          )}
          <Button icon={<ReloadOutlined />} onClick={onRefresh}>
            刷新数据
          </Button>
        </Flex>
      </Flex>
      <Space orientation="vertical" size={16} className="full-width">
        {runError && (
          <Alert type="warning" showIcon title="采集状态暂时不可用" description={runError} />
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
          <Alert type="warning" showIcon title="榜单已超过 26 小时未更新，请检查采集状态" />
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
              <div className="update-time">{formatTime(board.run?.finished_at ?? null)}</div>
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
              action={<Button onClick={() => onRefresh()}>重试</Button>}
            />
          ) : (
            <RankingTable items={board.items} loading={loading} empty={empty} onSelect={onSelect} />
          )}
        </Card>
      </Space>
    </>
  );
}
