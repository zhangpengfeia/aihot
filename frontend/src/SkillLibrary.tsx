/** 所有已识别项目的资料库，榜单前 20 之外的项目同样可被检索。 */
import { useEffect, useState } from 'react';
import {
  Alert,
  Button,
  Card,
  Empty,
  Flex,
  Input,
  Select,
  Space,
  Table,
  Tag,
  Typography,
} from 'antd';
import type { TableProps } from 'antd';
import { BookOutlined } from '@ant-design/icons';
import { get, formatTime, type Snapshot } from './api';
const { Paragraph, Text } = Typography;
export const SKILL_CATEGORIES = ['脚本写作', '配音', '字幕', '动画', '剪辑', '其他'];
export default function SkillLibrary({
  onSelect,
  tick,
}: {
  onSelect: (id: number) => void;
  tick: number;
}) {
  const [category, setCategory] = useState<string>();
  const [q, setQ] = useState('');
  const [page, setPage] = useState(1);
  const [data, setData] = useState<{ total: number; items: Snapshot[] }>({ total: 0, items: [] });
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  useEffect(() => {
    const controller = new AbortController();
    setLoading(true);
    setError('');
    const params = new URLSearchParams({ page: String(page), q });
    if (category) params.set('category', category);
    get<typeof data>(`/skills?${params}`, controller.signal)
      .then(setData)
      .catch((e) => {
        if (!controller.signal.aborted) setError((e as Error).message);
      })
      .finally(() => {
        if (!controller.signal.aborted) setLoading(false);
      });
    return () => controller.abort();
  }, [page, q, category, tick]);
  const columns: TableProps<Snapshot>['columns'] = [
    {
      title: '项目与用途',
      width: 430,
      render: (_, item) => (
        <div>
          <Button type="link" className="project-link" onClick={() => onSelect(item.id)}>
            {item.full_name}
          </Button>
          <Paragraph className="project-description" ellipsis={{ rows: 2 }}>
            {item.description}
          </Paragraph>
          <Space wrap>
            {item.categories?.map((c) => (
              <Tag color="blue" key={c}>
                {c}
              </Tag>
            ))}
          </Space>
        </div>
      ),
    },
    {
      title: '安装方式（原文摘录）',
      width: 320,
      render: (_, item) => (
        <Paragraph
          ellipsis={{ rows: 3, tooltip: false }}
          style={{ fontSize: 12, whiteSpace: 'pre-wrap', margin: 0 }}
        >
          {item.installation}
        </Paragraph>
      ),
    },
    {
      title: '许可证',
      dataIndex: 'license',
      width: 120,
      render: (value: string | null) => <Tag>{value || '未声明'}</Tag>,
    },
    {
      title: '最近观测',
      dataIndex: 'observed_at',
      width: 160,
      render: (value: string) => <Text type="secondary">{formatTime(value)}</Text>,
    },
    {
      title: '操作',
      width: 100,
      render: (_, item) => (
        <Button icon={<BookOutlined />} onClick={() => onSelect(item.id)}>
          详情
        </Button>
      ),
    },
  ];
  return (
    <Space orientation="vertical" size={16} className="full-width">
      <Card size="small">
        <Flex gap={12} wrap>
          <Input.Search
            aria-label="搜索 Skill"
            placeholder="搜索项目名称或介绍"
            allowClear
            onSearch={(value) => {
              setQ(value);
              setPage(1);
            }}
            style={{ width: 300 }}
          />
          <Select
            aria-label="Skill 用途"
            placeholder="全部用途"
            allowClear
            value={category}
            onChange={(value) => {
              setCategory(value);
              setPage(1);
            }}
            style={{ width: 180 }}
            options={SKILL_CATEGORIES.map((value) => ({ label: value, value }))}
          />
          <Text type="secondary">用途为多标签规则匹配；项目详情保留安装原文与许可证。</Text>
        </Flex>
      </Card>
      {error ? (
        <Alert type="error" showIcon title={error} />
      ) : (
        <Card className="ranking-card" title={`Skill 项目资料 · ${data.total} 个`}>
          <Table<Snapshot>
            rowKey="id"
            columns={columns}
            dataSource={data.items}
            loading={loading}
            scroll={{ x: 1100 }}
            pagination={{
              current: page,
              pageSize: 20,
              total: data.total,
              onChange: setPage,
              showSizeChanger: false,
            }}
            locale={{ emptyText: <Empty description="尚无匹配项目，请启动采集或切换分类。" /> }}
          />
        </Card>
      )}
    </Space>
  );
}
