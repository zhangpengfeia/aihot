import { BulbOutlined, ReloadOutlined } from '@ant-design/icons';
import {
  Alert,
  Badge,
  Button,
  Card,
  Col,
  Flex,
  Row,
  Space,
  Statistic,
  Tag,
  Typography,
} from 'antd';
import { useState } from 'react';
import type { Topic } from '../../types/knowledge';
import { formatTime } from '../../utils/date';
import { KnowledgeDetailDrawer } from './components/KnowledgeDetailDrawer';
import { KnowledgeFilters } from './components/KnowledgeFilters';
import { KnowledgeTable } from './components/KnowledgeTable';
import { useKnowledgeTopics } from './hooks/useKnowledgeTopics';
const { Title, Text, Paragraph } = Typography;
export default function KnowledgeLibraryPage() {
  const state = useKnowledgeTopics();
  const { data, meta, loading, error, refresh } = state;
  const [selected, setSelected] = useState<Topic | null>(null);
  const failed = meta.sources.filter((s) => s.enabled !== false && s.status === 'failed');
  return (
    <>
      <Flex justify="space-between" align="center" wrap gap={16} className="page-heading">
        <div>
          <Space>
            <Title level={2}>知识选题库</Title>
            <Tag color="purple">内容灵感</Tag>
          </Space>
          <Paragraph type="secondary">
            融合国内外 API、RSS
            与学术资料，覆盖热门趋势和考古、深海生物、声音景观等小众题材，支持细分标签搜索。
          </Paragraph>
        </div>
        <Button icon={<ReloadOutlined />} loading={loading} onClick={() => refresh()}>
          刷新数据
        </Button>
      </Flex>
      <Space orientation="vertical" size={16} className="full-width">
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Card>
              <Statistic title="已收录知识选题" value={meta.total} />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card>
              <Statistic title="可用细分标签" value={meta.tag_count ?? 0} />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card>
              <Statistic
                title="已运行采集来源"
                value={meta.sources.filter((s) => s.enabled !== false).length}
              />
            </Card>
          </Col>
        </Row>
        <Alert
          type="info"
          showIcon
          title="热点候选按发布日期排序，知识探索用于常青与小众题材；未接入阅读量，不能据此认定全网热门或冷门。"
        />
        {failed.length > 0 && (
          <Alert
            type="warning"
            showIcon
            title={`${failed.length} 个来源最近采集失败，其他来源与历史资料仍可用`}
            description={failed.map((s) => `${s.name}：${s.error}`).join('；')}
          />
        )}
        {meta.category_catalog && (
          <Alert
            type={meta.category_catalog.status === 'success' ? 'info' : 'warning'}
            showIcon
            title={
              meta.category_catalog.status === 'success'
                ? `远程分类目录包含 ${meta.category_catalog.remote_count} 个分类`
                : meta.category_catalog.error || '远程分类同步中，当前显示本地分类'
            }
            description={
              <>
                来源：
                <a href={meta.category_catalog.source_url} target="_blank" rel="noreferrer">
                  {meta.category_catalog.source_name}
                </a>{' '}
                · 最近同步：{formatTime(meta.category_catalog.updated_at)}。
                远程目录每日更新；筛选仅显示已有内容且未隐藏的分类。
              </>
            }
          />
        )}
        <KnowledgeFilters {...state} />
        {error ? (
          <Alert
            type="error"
            showIcon
            title="知识资料读取失败"
            description={error}
            action={<Button onClick={() => refresh()}>重试</Button>}
          />
        ) : (
          <Card
            title={
              <Space>
                <BulbOutlined />
                知识选题<Tag>{data.total} 条</Tag>
              </Space>
            }
            className="ranking-card"
          >
            <KnowledgeTable {...state} onSelect={setSelected} />
          </Card>
        )}
        <Card title="采集来源状态" size="small">
          <Flex gap={20} wrap>
            {meta.sources.length ? (
              meta.sources.map((s) => (
                <Space key={s.name} orientation="vertical" size={3}>
                  <Badge
                    status={
                      s.enabled === false
                        ? 'default'
                        : s.status === 'success'
                          ? 'success'
                          : s.status === 'pending'
                            ? 'processing'
                            : 'error'
                    }
                    text={`${s.name}${s.enabled === false ? '（已停用）' : ''}`}
                  />
                  <Text type="secondary" style={{ fontSize: 11 }}>
                    {s.display_category ?? s.category} · 最近成功：{formatTime(s.last_success)}
                  </Text>
                </Space>
              ))
            ) : (
              <Text type="secondary">知识采集进程尚未运行，无需 GitHub Token。</Text>
            )}
          </Flex>
        </Card>
      </Space>
      <KnowledgeDetailDrawer selected={selected} onClose={() => setSelected(null)} />
    </>
  );
}
