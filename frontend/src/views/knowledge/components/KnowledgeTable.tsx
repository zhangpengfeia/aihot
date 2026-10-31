import { BulbOutlined } from '@ant-design/icons';
import type { TableProps } from 'antd';
import { Button, Empty, Space, Table, Tag, Typography } from 'antd';
import { AddToBoard } from '../../../components/workspace/PersonalActions';
import type { Topic } from '../../../types/knowledge';
import { formatTime } from '../../../utils/date';
import type { useKnowledgeTopics } from '../hooks/useKnowledgeTopics';
const { Text, Paragraph } = Typography;
export function KnowledgeTable({
  data,
  loading,
  page,
  pageSize,
  setPage,
  setPageSize,
  onSelect,
}: Pick<
  ReturnType<typeof useKnowledgeTopics>,
  'data' | 'loading' | 'page' | 'pageSize' | 'setPage' | 'setPageSize'
> & { onSelect: (topic: Topic) => void }) {
  const columns: TableProps<Topic>['columns'] = [
    {
      title: '知识选题',
      key: 'topic',
      width: 440,
      render: (_, item) => (
        <div>
          <Button type="link" className="project-link" onClick={() => onSelect(item)}>
            {item.title}
          </Button>
          <Paragraph className="project-description" ellipsis={{ rows: 2 }}>
            {item.summary}
          </Paragraph>
          <Space wrap>
            {item.tags
              ?.filter((tag) => tag !== item.category)
              .slice(0, 4)
              .map((tag) => (
                <Tag key={tag} color="geekblue">
                  {tag}
                </Tag>
              ))}
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
          <Button icon={<BulbOutlined />} onClick={() => onSelect(item)}>
            选题资料
          </Button>
          <AddToBoard topicId={item.id} />
        </Space>
      ),
    },
  ];
  return (
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
  );
}
