import { BookOutlined } from '@ant-design/icons';
import type { TableProps } from 'antd';
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
import { useEffect, useState } from 'react';
import { get, readCache } from '../../api/http';
import { type Snapshot } from '../../types/skills';
import { formatTime } from '../../utils/date';
const { Paragraph, Text } = Typography;
export const SKILL_CATEGORIES = [
  'AI短视频与影音制作',
  'AI办公',
  '视频生成',
  '二维动画',
  '三维动画',
  '动画',
  '数字人',
  '脚本写作',
  '配音',
  '字幕',
  '剪辑',
  '音乐音效',
  '文档办公',
  '表格数据',
  '演示文稿',
  '会议助手',
  '知识检索',
  '办公自动化',
  '其他',
];
export default function SkillLibraryPage({
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
    const params = new URLSearchParams({ page: String(page), q });
    if (category) params.set('category', category);
    const path = `/skills?${params}`;
    // 命中缓存则不转圈，立即渲染旧结果并在后台刷新。
    if (readCache(path) === undefined) setLoading(true);
    setError('');
    get<typeof data>(path, controller.signal, { cache: true })
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
      title: '核心功能 / 适用场景',
      width: 320,
      render: (_, item) => (
        <Paragraph
          ellipsis={{ rows: 3, tooltip: false }}
          style={{ fontSize: 12, whiteSpace: 'pre-wrap', margin: 0 }}
        >
          {item.analysis
            ? `${item.analysis.core_features.join('；')}。适合：${item.analysis.use_cases.join('；')}`
            : '历史资料尚未分析，请查看详情'}
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
            aria-label="搜索 AI 项目"
            placeholder="搜索项目名称或介绍"
            allowClear
            onSearch={(value) => {
              setQ(value);
              setPage(1);
            }}
            style={{ width: 300 }}
          />
          <Select
            aria-label="项目用途"
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
        <Card className="ranking-card" title={`AI 项目资料 · ${data.total} 个`}>
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
