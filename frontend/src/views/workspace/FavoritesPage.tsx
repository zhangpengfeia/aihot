import {
  Alert,
  Button,
  Card,
  Empty,
  Flex,
  Input,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
  message,
} from 'antd';
import { useEffect, useState } from 'react';
import { write } from '../../api/http';
import { PageHeading as Heading } from '../../components/common/PageHeading';
import { PersonalButton } from '../../components/workspace/PersonalActions';
import { useResource } from '../../hooks/useResource';
import { type PersonalItem } from '../../types/workspace';
import { formatTime } from '../../utils/date';
const { Paragraph } = Typography;
export function FavoritesPage({
  tick,
  onSelect,
}: {
  tick: number;
  onSelect: (id: number) => void;
}) {
  const [q, setQ] = useState('');
  const [kind, setKind] = useState<string>();
  const [scope, setScope] = useState('favorites');
  const [page, setPage] = useState(1);
  const params = new URLSearchParams({ page: String(page), q });
  if (kind) params.set('kind', kind);
  if (scope === 'notes') params.set('all_records', 'true');

  const resource = useResource<{ total: number; items: PersonalItem[] }>(
    `/workspace/items?${params}`,
    tick,
  );
  const [notice, context] = message.useMessage();
  useEffect(() => {
    if (resource.data)
      setPage((current) => Math.min(current, Math.max(1, Math.ceil(resource.data!.total / 20))));
  }, [resource.data]);
  return (
    <>
      {context}
      <Heading
        title="收藏与个人备注"
        description="整理关注的项目和知识选题，备注与收藏保存在当前实例。"
        {...resource}
      />
      <Space orientation="vertical" size={16} className="full-width">
        <Card size="small">
          <Flex wrap gap={12}>
            <Input.Search
              aria-label="搜索收藏和备注"
              allowClear
              placeholder="搜索名称或备注"
              style={{ width: 280 }}
              onSearch={(v) => {
                setQ(v);
                setPage(1);
              }}
            />
            <Select
              aria-label="资料类型"
              allowClear
              placeholder="全部类型"
              value={kind}
              style={{ width: 150 }}
              options={[
                { value: 'repository', label: 'GitHub 项目' },
                { value: 'topic', label: '知识选题' },
              ]}
              onChange={(v) => {
                setKind(v);
                setPage(1);
              }}
            />
            <Select
              aria-label="收藏范围"
              value={scope}
              style={{ width: 190 }}
              options={[
                { value: 'favorites', label: '已收藏' },
                { value: 'notes', label: '全部收藏与备注记录' },
              ]}
              onChange={(v) => {
                setScope(v);
                setPage(1);
              }}
            />
          </Flex>
        </Card>
        {resource.error && <Alert type="error" title={resource.error} showIcon />}
        <Card>
          <Table<PersonalItem>
            rowKey="id"
            loading={resource.loading}
            dataSource={resource.data?.items ?? []}
            scroll={{ x: 850 }}
            pagination={{
              current: page,
              pageSize: 20,
              total: resource.data?.total ?? 0,
              showSizeChanger: false,
              onChange: setPage,
            }}
            locale={{
              emptyText: <Empty description="暂无收藏，可从项目或选题详情添加收藏和备注。" />,
            }}
            columns={[
              {
                title: '资料',
                render: (_, item) => (
                  <Space orientation="vertical">
                    <a href={item.url} target="_blank" rel="noreferrer">
                      {item.title}
                    </a>
                    <Space>
                      <Tag>{item.target_kind === 'repository' ? 'GitHub 项目' : '知识选题'}</Tag>
                      <Tag color={item.favorite ? 'gold' : undefined}>
                        {item.favorite ? '已收藏' : '仅保留记录'}
                      </Tag>
                    </Space>
                  </Space>
                ),
              },
              {
                title: '个人备注',
                dataIndex: 'note',
                width: 300,
                render: (v: string) => (
                  <Paragraph ellipsis={{ rows: 3 }} style={{ whiteSpace: 'pre-wrap' }}>
                    {v || '暂无备注'}
                  </Paragraph>
                ),
              },
              { title: '更新时间', dataIndex: 'updated_at', width: 170, render: formatTime },
              {
                title: '操作',
                width: 250,
                render: (_, item) => (
                  <Space wrap>
                    {item.snapshot_id && (
                      <Button onClick={() => onSelect(item.snapshot_id!)}>项目资料</Button>
                    )}
                    <PersonalButton
                      kind={item.target_kind}
                      targetId={item.target_id}
                      onSaved={resource.refresh}
                    />
                    <Popconfirm
                      title="删除此收藏和备注记录？"
                      description="不会删除原始项目或选题。"
                      onConfirm={async () => {
                        try {
                          await write(
                            `/workspace/items/${item.target_kind}/${item.target_id}`,
                            'DELETE',
                          );
                          resource.refresh();
                        } catch (e) {
                          notice.error((e as Error).message);
                        }
                      }}
                    >
                      <Button danger>删除</Button>
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      </Space>
    </>
  );
}
