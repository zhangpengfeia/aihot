import { Alert, Card, Empty, Space, Tag, Typography } from 'antd';
import { useResource } from '../../hooks/useResource';
import type { Topic } from '../../types/knowledge';
import type { PersonalItem } from '../../types/workspace';
import { PersonalButton, AddToBoard } from '../../components/workspace/PersonalActions';
export function KnowledgeDashboardCard({ tick }: { tick: number }) {
  const resource = useResource<{ items: Topic[] }>(
    '/knowledge/topics?page_size=8&sort_by=collected',
    tick,
  );
  return (
    <Card title="知识库 · 最新选题" loading={resource.loading}>
      {resource.error && <Alert type="error" title={resource.error} />}
      {!resource.loading && !resource.data?.items.length && <Empty description="暂无知识选题" />}
      <Space orientation="vertical" className="full-width" size={16}>
        {resource.data?.items.map((item) => (
          <div key={item.id}>
            <Space wrap>
              <Tag>{item.category}</Tag>
              <Typography.Link href={item.source_url} target="_blank" rel="noreferrer">
                {item.title}
              </Typography.Link>
            </Space>
            <div style={{ marginTop: 8 }}>
              <Space wrap>
                <PersonalButton kind="topic" targetId={item.id} />
                <AddToBoard topicId={item.id} />
              </Space>
            </div>
          </div>
        ))}
      </Space>
    </Card>
  );
}
export function FavoritesDashboardCard({ tick }: { tick: number }) {
  const resource = useResource<{ items: PersonalItem[] }>('/workspace/items?page_size=8', tick);
  return (
    <Card title="我的收藏" loading={resource.loading}>
      {resource.error && <Alert type="error" title={resource.error} />}
      {!resource.loading && !resource.data?.items.length && <Empty description="还没有收藏" />}
      <Space orientation="vertical" className="full-width">
        {resource.data?.items.map((item) => (
          <div key={item.id}>
            <Typography.Text>{item.title}</Typography.Text>
            {item.note && (
              <Typography.Paragraph type="secondary" ellipsis={{ rows: 2 }}>
                {item.note}
              </Typography.Paragraph>
            )}
          </div>
        ))}
      </Space>
    </Card>
  );
}
