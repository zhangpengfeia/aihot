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
  Segmented,
  Space,
  Tag,
  Typography,
} from 'antd';
import { useResource } from '../../hooks/useResource';
import { formatTime } from '../../utils/date';
import { legacyPlatforms } from '../../utils/hotlists';
import type { HotPlatform, HotSource } from '../../types/hotlists';
import { PersonalButton, AddToBoard } from '../../components/workspace/PersonalActions';
import { PlatformPicker } from './components/PlatformPicker';
export type { HotSource } from '../../types/hotlists';
export function HotListsPage({
  tick,
  compact = false,
  platformIds = [],
}: {
  tick: number;
  compact?: boolean;
  platformIds?: string[];
}) {
  const resource = useResource<{ items: HotSource[]; platforms?: HotPlatform[] }>(
    '/knowledge/hotlists',
    tick,
  );
  const [query, setQuery] = useState('');
  const [region, setRegion] = useState('全部');
  const [selected, setSelected] = useState<string[]>([]);
  const sources = resource.data?.platforms ?? legacyPlatforms(resource.data?.items ?? []);
  const filters = compact ? platformIds : selected;
  const visible = sources.filter(
    (source) =>
      (region === '全部' || source.region === region) &&
      (!filters.length || filters.includes(source.id)) &&
      (!query ||
        `${source.name} ${source.category}`.toLowerCase().includes(query.toLowerCase()) ||
        source.items.some((item) => item.title.toLowerCase().includes(query.toLowerCase()))),
  );
  const displayed =
    compact && !filters.length
      ? visible
          .filter((source) => source.connection_status === 'configured')
          .sort((a, b) => Number(!!b.items.length) - Number(!!a.items.length))
          .slice(0, 3)
      : visible;
  return (
    <Space orientation="vertical" className="full-width" size={16}>
      {!compact && (
        <>
          <Flex justify="space-between" align="center" wrap gap={12}>
            <div>
              <Typography.Title level={2}>全网热搜</Typography.Title>
              <Typography.Text type="secondary">
                按平台展示最近一次成功采集的榜单，预留平台暂不采集。
              </Typography.Text>
            </div>
            <Button loading={resource.loading} onClick={resource.refresh}>
              刷新已存榜单
            </Button>
          </Flex>
          <Card size="small">
            <Flex gap={12} wrap align="center">
              <PlatformPicker platforms={sources} value={selected} onChange={setSelected} />
              <Segmented
                aria-label="平台地区筛选"
                value={region}
                options={['全部', '国内', '国外']}
                onChange={setRegion}
              />
              <Input.Search
                aria-label="搜索热搜词"
                placeholder="搜索平台或热搜词"
                allowClear
                onSearch={setQuery}
                style={{ width: 260, maxWidth: '100%' }}
              />
              <Typography.Text type="secondary">{visible.length} 个平台</Typography.Text>
            </Flex>
          </Card>
        </>
      )}
      {resource.error && <Alert type="error" title={resource.error} />}
      {!resource.loading && !displayed.length && <Empty description="没有匹配的平台或已配置榜单" />}
      <Row gutter={[16, 16]}>
        {displayed.map((source) => (
          <Col key={source.id} xs={24} lg={compact ? 24 : 12} xl={compact ? 24 : 8}>
            <Card
              size={compact ? 'small' : 'default'}
              title={source.name}
              extra={
                <Tag color={source.status === 'success' ? 'green' : 'default'}>
                  {source.connection_status === 'reserved'
                    ? '预留'
                    : !source.enabled
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
                {source.region} · {source.category} ·{' '}
                {source.connection_status === 'reserved'
                  ? '暂未接入 API'
                  : `最近榜单：${formatTime(source.observed_at)}`}
              </Typography.Paragraph>
              {source.error && (
                <Alert
                  type="warning"
                  title="最近采集失败，以下可能是历史榜单"
                  description={source.error}
                />
              )}
              {!source.items.length && (
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={
                    source.connection_status === 'reserved'
                      ? '平台已预留，暂未接入采集接口'
                      : source.enabled
                        ? '暂无榜单，等待管理员或线上定时采集'
                        : '接口已配置，待测试启用'
                  }
                />
              )}
              <Space orientation="vertical" className="full-width" size={16}>
                {source.items
                  .filter(
                    (item) =>
                      !query ||
                      source.name.includes(query) ||
                      item.title.toLowerCase().includes(query.toLowerCase()),
                  )
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
                        <Space wrap style={{ marginTop: 8 }}>
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
