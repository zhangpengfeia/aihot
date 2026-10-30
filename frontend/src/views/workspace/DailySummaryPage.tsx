import {
Alert,
Button,
Card,
Col,
Empty,
Row,
Space,
Spin,
Table,
Tag,
Typography
} from "antd";
import { PageHeading as Heading } from '../../components/common/PageHeading';
import { useResource } from '../../hooks/useResource';
import { type Snapshot } from '../../types/skills';
import type { Summary } from '../../types/workspace-responses';
import { formatTime } from '../../utils/date';
const {Title,Text,Paragraph}=Typography;
export function DailySummaryPage({
  tick,
  onSelect,
}: {
  tick: number;
  onSelect: (id: number) => void;
}) {
  const resource = useResource<Summary>('/workspace/daily-summary', tick);
  const data = resource.data;
  function list(items: Snapshot[], mode: 'new' | 'rise' | 'growth') {
    return (
      <Table<Snapshot>
        rowKey="repo_id"
        size="small"
        pagination={false}
        dataSource={items}
        scroll={{ x: 460 }}
        locale={{ emptyText: <Empty description="暂无符合条件的项目" /> }}
        columns={[
          {
            title: '项目',
            render: (_, item) => (
              <Button type="link" className="project-link" onClick={() => onSelect(item.id)}>
                {item.full_name}
              </Button>
            ),
          },
          {
            title: mode === 'growth' ? '24h 净增 Star' : mode === 'rise' ? '排名变化' : '本期排名',
            width: 150,
            render: (_, item) =>
              mode === 'growth' ? (
                <Text type="success">+{item.delta_24h?.toLocaleString()}</Text>
              ) : mode === 'rise' ? (
                <Tag color="green">
                  ↑ {(item as Summary['risers'][number]).rank_change} 名 · #{item.rank}
                </Tag>
              ) : (
                <Tag>#{item.rank}</Tag>
              ),
          },
        ]}
      />
    );
  }
  return (
    <>
      <Heading
        title="每日变化摘要"
        description="对比最近两次成功的累计 Star 榜，快速查看值得关注的变化。"
        {...resource}
      />
      <Space orientation="vertical" size={16} className="full-width">
        {resource.error && <Alert type="error" showIcon title={resource.error} />}
        <Spin spinning={resource.loading}>
          <Card>
            {data?.current ? (
              <Space orientation="vertical">
                <Text>
                  本期：{formatTime(data.current.finished_at)} · 前期：
                  {formatTime(data.previous?.finished_at ?? null)}
                </Text>
                <Text type="secondary">
                  {data.previous
                    ? '新上榜指未进入前期累计 Star 榜，不代表新建仓库。'
                    : '只有一期成功榜单，暂不判断新上榜和名次变化。'}{' '}
                  24h 增长使用已有观测基线，缺失时不推算。
                </Text>
              </Space>
            ) : (
              <Empty description="暂无成功采集记录" />
            )}
          </Card>
        </Spin>
        <Row gutter={[16, 16]}>
          <Col xs={24} xl={12}>
            <Card title={`新上榜 · ${data?.new_entries.length ?? 0}`}>
              {list(data?.new_entries ?? [], 'new')}
            </Card>
          </Col>
          <Col xs={24} xl={12}>
            <Card title={`排名上升 · ${data?.risers.length ?? 0}`}>
              {list(data?.risers ?? [], 'rise')}
            </Card>
          </Col>
        </Row>
        <Card title="24h Star 正增长 · 前 10 个项目">{list(data?.growth ?? [], 'growth')}</Card>
      </Space>
    </>
  );
}
