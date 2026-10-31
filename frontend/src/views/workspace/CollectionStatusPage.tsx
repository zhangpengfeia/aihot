import { useEffect, useState } from 'react';
import { get, write } from '../../api/http';
import type { User } from '../users/UserManagementPage';
import {
  Button,
  Modal,
  message,
  Alert,
  Card,
  Col,
  Progress,
  Row,
  Space,
  Statistic,
  Table,
  Tag,
  Typography,
} from 'antd';
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
  const { data: user } = useResource<User | null>('/auth/me', tick);
  const [pending, setPending] = useState<string | null>(null);
  const [confirmKind, setConfirmKind] = useState<string | null>(null);
  const [taskId, setTaskId] = useState<string | null>(null);
  const [task, setTask] = useState<{
    status: string;
    progress: number;
    logs: { time: string; message: string }[];
  } | null>(null);
  const [pollError, setPollError] = useState('');
  const [showProgress, setShowProgress] = useState(false);
  const active = !!taskId && (!task || ['pending', 'running'].includes(task.status));
  useEffect(() => {
    if (!taskId) return;
    const controller = new AbortController();
    let timer: ReturnType<typeof setTimeout>;
    const poll = async () => {
      try {
        const result = await get<NonNullable<typeof task>>(
          `/admin/collection-tasks/${taskId}`,
          controller.signal,
        );
        if (controller.signal.aborted) return;
        setTask(result);
        setPollError('');
        if (!['pending', 'running'].includes(result.status)) {
          resource.refresh();
          return;
        }
      } catch {
        if (controller.signal.aborted) return;
        setPollError('进度读取失败，正在重试。采集可能仍在后台运行。');
      }
      timer = setTimeout(poll, 2000);
    };
    void poll();
    return () => {
      controller.abort();
      clearTimeout(timer);
    };
  }, [taskId]);
  const trigger = async (kind: string) => {
    if (pending || active) return;
    setPending(kind);
    try {
      const result = await write<{ task_id: string }>(`/admin/collect/${kind}`, 'POST', {});
      setConfirmKind(null);
      setTask(null);
      setPollError('');
      setTaskId(result.task_id);
      setShowProgress(true);
    } catch (e) {
      message.error((e as Error).message);
    } finally {
      setPending(null);
    }
  };
  return (
    <>
      <Modal
        title="确认立即采集？"
        open={confirmKind !== null}
        onCancel={() => {
          if (!pending) setConfirmKind(null);
        }}
        onOk={() => {
          if (confirmKind) void trigger(confirmKind);
        }}
        okText="确认采集"
        cancelText="取消"
        confirmLoading={!!pending}
        cancelButtonProps={{ disabled: !!pending }}
        closable={!pending}
        maskClosable={false}
        keyboard={!pending}
      >
        <Alert
          showIcon
          type="warning"
          title={`是否立即触发${confirmKind === 'github' ? ' GitHub ' : '知识库'}采集接口？`}
          description="确认后将启动后台采集并请求外部接口。GitHub 当周已完成的批次会自动跳过，知识库按半小时窗口去重。"
        />
      </Modal>
      <Modal
        title="采集进度与日志"
        open={showProgress}
        width={760}
        onCancel={() => setShowProgress(false)}
        footer={
          <Button onClick={() => setShowProgress(false)}>{active ? '后台运行' : '关闭'}</Button>
        }
      >
        <Space orientation="vertical" className="full-width">
          <Text>
            {task
              ? ({
                  pending: '等待执行',
                  running: '采集中',
                  success: '采集完成',
                  partial: '采集结束，部分来源失败',
                  failed: '采集失败',
                  skipped: '已跳过',
                }[task.status] ?? task.status)
              : '等待采集任务启动'}
          </Text>
          <Progress
            percent={task?.progress ?? 0}
            status={
              task?.status === 'failed' || task?.status === 'partial'
                ? 'exception'
                : active
                  ? 'active'
                  : 'normal'
            }
          />
          <Text type="secondary">
            进度按已处理的项目或来源计算，每两秒更新。关闭窗口后仍会继续采集。
          </Text>
          {pollError && <Alert type="warning" showIcon title={pollError} />}
          <div
            role="log"
            aria-label="采集日志"
            style={{
              maxHeight: 360,
              overflow: 'auto',
              whiteSpace: 'pre-wrap',
              overflowWrap: 'anywhere',
              background: '#f5f5f5',
              padding: 12,
            }}
          >
            {task?.logs.map((log, index) => (
              <div key={index}>
                {formatTime(log.time)} · {log.message}
              </div>
            ))}
            {!task?.logs.length && '等待日志…'}
          </div>
        </Space>
      </Modal>
      <Heading
        title="采集状态面板"
        description="查看采集记录和计划时间，页面每分钟刷新。"
        {...resource}
      />
      <Space orientation="vertical" size={16} className="full-width">
        {user?.role === 'admin' && (
          <Space wrap>
            <Button
              type="primary"
              disabled={!!pending || active}
              loading={pending === 'github'}
              onClick={() => setConfirmKind('github')}
            >
              立即采集 GitHub
            </Button>
            <Button
              disabled={!!pending || active}
              loading={pending === 'knowledge'}
              onClick={() => setConfirmKind('knowledge')}
            >
              立即采集知识库
            </Button>
            {taskId && <Button onClick={() => setShowProgress(true)}>查看采集进度</Button>}
          </Space>
        )}
        {resource.error && <Alert type="error" showIcon title={resource.error} />}
        <Alert
          type="info"
          showIcon
          title="GitHub 每周一北京时间 00:00 更新 AI 项目前 100 周榜；知识来源每半小时采集。"
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
        {data?.storage && (
          <Card title="采集数据存储">
            <Text>
              估算已用 {(data.storage.used_bytes / 1_000_000_000).toFixed(3)} GB / 上限{' '}
              {data.storage.limit_bytes / 1_000_000_000} GB
            </Text>
            <Progress
              percent={data.storage.usage_percent}
              status={data.storage.over_limit ? 'exception' : 'normal'}
            />
            <Paragraph type="secondary">
              采集时达到阈值自动删除最旧数据，目标降至{' '}
              {Math.round((data.storage.cleanup_target_bytes / data.storage.limit_bytes) * 100)}%。
              保留收藏、备注、创作引用、各项目最新资料和近期榜单；空间仍不足时暂停采集。
              容量为有效数据及行索引开销估算，数据库文件不会随删除立即缩小。
            </Paragraph>
          </Card>
        )}
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
