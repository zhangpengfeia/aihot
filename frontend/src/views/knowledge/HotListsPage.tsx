import { useState } from 'react';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Empty,
  Flex,
  Input,
  Row,
  Space,
  Tag,
  Typography,
} from 'antd';
import { useResource } from '../../hooks/useResource';
import { formatTime } from '../../utils/date';
import { PersonalButton, AddToBoard } from '../../components/workspace/PersonalActions';
export interface HotSource {
  id: number;
  name: string;
  enabled: boolean;
  status: string;
  error: string | null;
  observed_at: string | null;
  items: {
    id: number;
    title: string;
    source_url: string;
    score: number | null;
    score_label?: string | null;
    rank: number;
  }[];
}
export function HotListsPage({ tick, compact = false }: { tick: number; compact?: boolean }) {
  const resource = useResource<{ items: HotSource[] }>('/knowledge/hotlists', tick);
  const [q, setQ] = useState('');
  const [platform, setPlatform] = useState<number | null>(null);
  const sources = resource.data?.items ?? [];
  const visible = sources.filter(
    (source) =>
      (platform === null || source.id === platform) &&
      (!q || source.name.includes(q) || source.items.some((i) => i.title.includes(q))),
  );
  return (
    <Space orientation="vertical" className="full-width" size={16}>
      {!compact && (
        <Flex justify="space-between" wrap gap={12}>
          <div>
            <Typography.Title level={2}>全网热搜</Typography.Title>
            <Typography.Text type="secondary">
              按来源展示最后一次成功采集的榜单，保留返回顺序；各平台指标不可直接比较。
            </Typography.Text>
          </div>
          <Button onClick={resource.refresh} loading={resource.loading}>
            刷新已存榜单
          </Button>
        </Flex>
      )}
      {resource.error && <Alert type="error" title={resource.error} />}
      {!compact && (
        <>
          <Alert
            type="info"
            title="百度、微博、小红书等使用社区聚合 API，非平台官方服务。备用模板需测试启用，刷新页面不会执行采集。"
          />
          <Input.Search
            placeholder="搜索平台或热搜词"
            allowClear
            onSearch={setQ}
            aria-label="搜索平台或热搜词"
          />
          <Flex gap={8} wrap>
            <Button
              type={platform === null ? 'primary' : 'default'}
              onClick={() => setPlatform(null)}
            >
              全部平台
            </Button>
            {sources.map((source) => (
              <Button
                key={source.id}
                type={platform === source.id ? 'primary' : 'default'}
                onClick={() => setPlatform(source.id)}
              >
                {source.name.replace('热搜 · ', '')}
              </Button>
            ))}
          </Flex>
        </>
      )}
      {!resource.loading && !sources.length && (
        <Empty description="尚未配置热搜来源，请先执行数据库迁移导入来源，再由管理员采集" />
      )}
      <Row gutter={[16, 16]}>
        {(compact ? visible.slice(0, 3) : visible).map((source) => (
          <Col key={source.id} xs={24} lg={compact ? 24 : 12} xl={compact ? 24 : 8}>
            <Card
              title={source.name.replace('热搜 · ', '')}
              size={compact ? 'small' : 'default'}
              extra={
                <Tag color={source.status === 'success' ? 'green' : 'default'}>
                  {!source.enabled
                    ? '未启用'
                    : source.status === 'success'
                      ? '已采集'
                      : source.status === 'failed'
                        ? '采集失败'
                        : '待采集'}
                </Tag>
              }
            >
              <Typography.Paragraph type="secondary">
                最近成功榜单：{formatTime(source.observed_at)}
              </Typography.Paragraph>
              {source.error && (
                <Alert
                  type="warning"
                  title="最近请求失败，以下可能是历史榜单"
                  description={source.error}
                />
              )}
              {!source.items.length && (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={source.enabled ? '暂无榜单，等待管理员或线上定时采集' : '待测试启用'}
                />
              )}
              <Space orientation="vertical" className="full-width" size={16}>
                {source.items
                  .filter((item) => !q || source.name.includes(q) || item.title.includes(q))
                  .slice(0, compact ? 5 : 50)
                  .map((item) => (
                    <div key={`${item.id}-${item.rank}`}>
                      <Space align="start">
                        <Badge count={item.rank} color={item.rank <= 3 ? '#f97316' : '#94a3b8'} />
                        <Typography.Link href={item.source_url} target="_blank" rel="noreferrer">
                          {item.title}
                        </Typography.Link>
                      </Space>
                      {(item.score_label || item.score !== null) && (
                        <Typography.Text type="secondary">
                          {' '}
                          · 来源指标 {item.score_label ?? item.score?.toLocaleString()}
                        </Typography.Text>
                      )}
                      {!compact && (
                        <Space style={{ marginTop: 8 }} wrap>
                          <PersonalButton kind="topic" targetId={item.id} />
                          <AddToBoard topicId={item.id} />
                        </Space>
                      )}
                    </div>
                  ))}
              </Space>
            </Card>
          </Col>
        ))}
      </Row>
    </Space>
  );
}
