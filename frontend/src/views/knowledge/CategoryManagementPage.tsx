import { ReloadOutlined } from '@ant-design/icons';
import {
  Alert,
  AutoComplete,
  Button,
  Card,
  Flex,
  Input,
  message,
  Modal,
  Popconfirm,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';
import { useState } from 'react';
import { write } from '../../api/http';
import { useResource as useManagement } from '../../hooks/useResource';
import type { CategoryResponse, CategoryRow } from '../../types/knowledge-management';
import { formatTime } from '../../utils/date';
const { Title, Text, Paragraph } = Typography;
export function CategoryManagementPage({ tick }: { tick: number }) {
  const resource = useManagement<CategoryResponse>('/knowledge/manage/categories', tick);
  const [q, setQ] = useState('');
  const [scope, setScope] = useState('all');
  const [source, setSource] = useState<CategoryRow | null>(null);
  const [target, setTarget] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, context] = message.useMessage();
  const items = resource.data?.items ?? [];
  async function visibility(row: CategoryRow) {
    try {
      await write('/knowledge/manage/category-visibility', 'PUT', {
        name: row.name,
        hidden: !row.hidden,
      });
      resource.refresh();
    } catch (e) {
      notice.error((e as Error).message);
    }
  }
  const filtered = items.filter(
    (row) =>
      `${row.name} ${row.canonical_name}`.includes(q) &&
      (scope === 'all' ||
        (scope === 'populated' && row.total_count > 0 && !row.is_alias) ||
        (scope === 'empty' && row.total_count === 0) ||
        (scope === 'hidden' && row.hidden) ||
        (scope === 'aliases' && row.is_alias)),
  );
  const catalog = resource.data?.catalog;
  return (
    <>
      {context}
      <Flex justify="space-between" align="center" wrap gap={16} className="page-heading">
        <div>
          <Title level={2}>分类整理</Title>
          <Paragraph type="secondary">
            合并同义分类、整理筛选选项，保留每条选题的原始分类。
          </Paragraph>
        </div>
        <Button icon={<ReloadOutlined />} onClick={resource.refresh} loading={resource.loading}>
          刷新
        </Button>
      </Flex>
      <Space orientation="vertical" size={16} className="full-width">
        <Alert
          type="info"
          showIcon
          title="选题筛选只显示已有内容且未隐藏的分类。"
          description="合并后原分类作为别名，查询会包含全部同义分类；可以随时撤销合并。隐藏只影响筛选选项，题库内容仍保留。"
        />
        {catalog && (
          <Alert
            type={catalog.status === 'success' ? 'info' : 'warning'}
            showIcon
            title={catalog.error || '远程分类目录已同步'}
            description={
              <span>
                目录来源：
                <a href={catalog.source_url} target="_blank" rel="noreferrer">
                  {catalog.source_name}
                </a>{' '}
                · 最近同步：{formatTime(catalog.updated_at)}。没有内容的分类仅在管理页展示。
              </span>
            }
          />
        )}
        {resource.error && <Alert type="error" showIcon title={resource.error} />}
        <Card size="small">
          <Flex gap={12} wrap>
            <Input.Search
              aria-label="搜索分类"
              placeholder="搜索分类或合并后的名称"
              allowClear
              onSearch={setQ}
              style={{ width: 300 }}
            />
            <Select
              aria-label="分类范围"
              value={scope}
              onChange={setScope}
              style={{ width: 180 }}
              options={[
                { value: 'all', label: '全部分类' },
                { value: 'populated', label: '已有内容' },
                { value: 'empty', label: '暂无内容' },
                { value: 'hidden', label: '已隐藏' },
                { value: 'aliases', label: '已合并的别名' },
              ]}
            />
          </Flex>
        </Card>
        <Card>
          <Table<CategoryRow>
            rowKey="name"
            dataSource={filtered}
            loading={resource.loading}
            scroll={{ x: 820 }}
            pagination={{ pageSize: 15, showSizeChanger: false }}
            columns={[
              {
                title: '分类名称',
                dataIndex: 'name',
                render: (name: string) => <Text strong>{name}</Text>,
              },
              {
                title: '合并后名称',
                render: (_, row) =>
                  row.is_alias ? <Tag color="blue">→ {row.canonical_name}</Tag> : row.name,
              },
              { title: '原分类内容数', dataIndex: 'topic_count' },
              { title: '合并后内容数', dataIndex: 'total_count' },
              {
                title: '筛选状态',
                render: (_, row) => (
                  <Tag
                    color={
                      row.hidden
                        ? undefined
                        : row.total_count && !row.is_alias
                          ? 'green'
                          : 'default'
                    }
                  >
                    {row.hidden
                      ? '已隐藏'
                      : row.is_alias
                        ? '使用合并后的分类'
                        : row.total_count
                          ? '可筛选'
                          : '暂无内容'}
                  </Tag>
                ),
              },
              {
                title: '操作',
                width: 260,
                render: (_, row) => (
                  <Space wrap>
                    <Button
                      onClick={() => {
                        setSource(row);
                        setTarget('');
                        setError('');
                      }}
                    >
                      合并到…
                    </Button>
                    {row.is_alias ? (
                      <Popconfirm
                        title={`撤销“${row.name}”的合并？`}
                        description="该分类将恢复独立展示，历史内容不会改变。"
                        onConfirm={async () => {
                          try {
                            await write('/knowledge/manage/category-unmerge', 'POST', {
                              name: row.name,
                            });
                            resource.refresh();
                          } catch (e) {
                            notice.error((e as Error).message);
                          }
                        }}
                      >
                        <Button>撤销合并</Button>
                      </Popconfirm>
                    ) : (
                      <Button onClick={() => visibility(row)}>
                        {row.hidden ? '恢复显示' : '隐藏'}
                      </Button>
                    )}
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      </Space>
      <Modal
        title="合并同义分类"
        open={source !== null}
        onCancel={() => setSource(null)}
        confirmLoading={busy}
        okText="合并"
        cancelText="取消"
        okButtonProps={{ disabled: !target.trim() }}
        onOk={async () => {
          if (!source) return;
          setBusy(true);
          setError('');
          try {
            await write('/knowledge/manage/category-merge', 'POST', {
              source: source.name,
              target: target.trim(),
            });
            setSource(null);
            resource.refresh();
            notice.success('分类合并规则已保存');
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        <Space orientation="vertical" className="full-width" size={16}>
          {error && <Alert type="error" showIcon title={error} />}
          <Paragraph>
            将“{source?.name}”并入目标分类。原始内容不改写，可以在列表中撤销合并。
          </Paragraph>
          <label htmlFor="category-merge-target">目标分类</label>
          <AutoComplete
            id="category-merge-target"
            className="full-width"
            value={target}
            onChange={setTarget}
            options={items
              .filter((row) => row.name !== source?.name && !row.is_alias)
              .map((row) => ({ value: row.name }))}
            filterOption={(input, option) => String(option?.value).includes(input)}
            maxLength={50}
            placeholder="选择现有分类或输入新名称"
          />
        </Space>
      </Modal>
    </>
  );
}
