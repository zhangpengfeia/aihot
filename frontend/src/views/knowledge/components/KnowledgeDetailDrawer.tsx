import { DownloadOutlined, LinkOutlined } from '@ant-design/icons';
import { Button, Card, Descriptions, Drawer, Space, Tag, Typography } from 'antd';
import { AddToBoard, PersonalButton } from '../../../components/workspace/PersonalActions';
import type { Topic } from '../../../types/knowledge';
import { formatTime } from '../../../utils/date';
const { Title, Text, Paragraph } = Typography;
export function KnowledgeDetailDrawer({
  selected,
  onClose,
}: {
  selected: Topic | null;
  onClose: () => void;
}) {
  return (
    <Drawer
      title="知识选题资料"
      open={selected !== null}
      onClose={onClose}
      size={Math.min(760, window.innerWidth)}
    >
      {selected && (
        <Space orientation="vertical" size={24} className="full-width">
          <div>
            <Title level={3}>{selected.title}</Title>
            <Space wrap style={{ marginBottom: 16 }}>
              <PersonalButton kind="topic" targetId={selected.id} />
              <AddToBoard topicId={selected.id} />
            </Space>
            <Space>
              <Tag color="blue">{selected.category}</Tag>
              <Tag>{selected.region}</Tag>
              <Tag color="purple">{selected.topic_kind}</Tag>
            </Space>
          </div>
          <Descriptions
            column={1}
            bordered
            size="small"
            items={[
              { key: 'source', label: '来源', children: selected.source_name },
              {
                key: 'channels',
                label: '融合渠道',
                children: selected.channels?.map((c) => c.name).join('、') || selected.source_name,
              },
              { key: 'region', label: '题材地区', children: selected.region },
              { key: 'region_basis', label: '地区判断依据', children: selected.region_basis },
              {
                key: 'published',
                label: '发布日期',
                children: selected.published_at
                  ? formatTime(selected.published_at)
                  : '原来源未提供',
              },
              {
                key: 'collected',
                label: '首次采集',
                children: formatTime(selected.collected_at),
              },
            ]}
          />
          <div>
            <Title level={5}>知识摘要</Title>
            <Tag>{selected.summary_method}</Tag>
            <Paragraph style={{ marginTop: 12, whiteSpace: 'pre-wrap' }}>
              {selected.summary}
            </Paragraph>
          </div>
          <Card title="视频切入角度" size="small">
            <Paragraph>{selected.video_angle}</Paragraph>
            <Text type="secondary">
              规则模板建议，不代表已核实事实结论；发布前阅读原文与核对资料。
            </Text>
          </Card>
          <Space wrap>
            <Button
              type="primary"
              icon={<LinkOutlined />}
              href={selected.source_url}
              target="_blank"
              rel="noreferrer"
            >
              阅读原始来源
            </Button>
            <Button
              icon={<DownloadOutlined />}
              href={`/api/knowledge/topics/${selected.id}/markdown`}
            >
              下载 Markdown
            </Button>
          </Space>
        </Space>
      )}
    </Drawer>
  );
}
