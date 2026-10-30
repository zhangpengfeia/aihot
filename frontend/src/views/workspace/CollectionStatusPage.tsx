import { Alert, Card, Col, Row, Space, Statistic, Table, Tag, Typography } from 'antd';
import { PageHeading as Heading } from '../../components/common/PageHeading';
import { useResource } from '../../hooks/useResource';
import { type Run } from '../../types/skills';
import type { Status } from '../../types/workspace-responses';
import { formatTime } from '../../utils/date';
const { Text, Paragraph } = Typography;
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
