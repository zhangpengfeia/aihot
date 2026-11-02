import { PlusOutlined, ReloadOutlined } from '@ant-design/icons';
import {
  Alert,
  Button,
  Card,
  Col,
  Flex,
  Input,
  message,
  Popconfirm,
  Row,
  Space,
  Statistic,
  Switch,
  Table,
  Tag,
  Typography,
} from 'antd';
import { useState } from 'react';
import { write } from '../../api/http';
import { useResource as useManagement } from '../../hooks/useResource';
import type { CategoryResponse, ManagedSource, Preview } from '../../types/knowledge-management';
import { formatTime } from '../../utils/date';
import { InterfaceFormModal } from './components/InterfaceFormModal';
import { InterfacePreviewModal } from './components/InterfacePreviewModal';
const { Title, Text, Paragraph } = Typography;
export function InterfaceManagementPage({ tick }: { tick: number }) {
  const resource = useManagement<{ items: ManagedSource[] }>('/knowledge/manage/sources', tick);
  const categories = useManagement<CategoryResponse>('/knowledge/manage/categories', tick);
  const [editing, setEditing] = useState<ManagedSource | null>(null);
  const [open, setOpen] = useState(false);
  const [bulkBusy, setBulkBusy] = useState<boolean | null>(null);
  const [busyId, setBusyId] = useState<number | null>(null);
  const [previewSource, setPreviewSource] = useState<ManagedSource | null>(null);
  const [preview, setPreview] = useState<Preview | null>(null);
  const [testing, setTesting] = useState(false);
  const [testError, setTestError] = useState('');
  const [q, setQ] = useState('');
  const [notice, context] = message.useMessage();
  const rows = resource.data?.items ?? [];
  const options = (categories.data?.items ?? [])
    .filter((item) => !item.is_alias)
    .map((item) => ({ value: item.name }));
  function edit(source: ManagedSource | null) {
    setEditing(source);
    setOpen(true);
  }
  async function setAllEnabled(enabled: boolean) {
    setBulkBusy(enabled);
    try {
      const result = await write<{ changed: number }>('/knowledge/manage/sources/enabled', 'PUT', {
        enabled,
      });
      notice.success(`已${enabled ? '启用' : '关闭'} ${result.changed} 个来源，下一轮采集生效`);
      resource.refresh();
    } catch (e) {
      notice.error((e as Error).message);
    } finally {
      setBulkBusy(null);
    }
  }
  async function test(source: ManagedSource) {
    setPreviewSource(source);
    setPreview(null);
    setTestError('');
    setTesting(true);
    try {
      setPreview(await write<Preview>(`/knowledge/manage/sources/${source.id}/test`, 'POST', {}));
    } catch (e) {
      setTestError((e as Error).message);
    } finally {
      setTesting(false);
      resource.refresh();
    }
  }
  return (
    <>
      {context}
      <Flex justify="space-between" align="center" wrap gap={16} className="page-heading">
        <div>
          <Title level={2}>采集接口管理</Title>
          <Paragraph type="secondary">
            统一管理 RSS / Atom、Hacker News、百科与通用 JSON API；配置变更在下一轮采集生效。
          </Paragraph>
        </div>
        <Space wrap>
          <Button
            onClick={() => setAllEnabled(true)}
            loading={bulkBusy === true}
            disabled={
              bulkBusy !== null ||
              busyId !== null ||
              resource.loading ||
              !rows.some((row) => !row.enabled)
            }
            title="启用全部来源，包含搜索结果以外的来源"
          >
            全部启用
          </Button>
          <Button
            onClick={() => setAllEnabled(false)}
            loading={bulkBusy === false}
            disabled={
              bulkBusy !== null ||
              busyId !== null ||
              resource.loading ||
              !rows.some((row) => row.enabled)
            }
            title="关闭全部来源，保留已采集数据；正在运行的采集不受影响"
          >
            全部关闭
          </Button>
          <Button icon={<ReloadOutlined />} onClick={resource.refresh} loading={resource.loading}>
            刷新
          </Button>
          <Button type="primary" icon={<PlusOutlined />} onClick={() => edit(null)}>
            新增接口
          </Button>
        </Space>
      </Flex>
      <Space orientation="vertical" size={16} className="full-width">
        <Row gutter={[16, 16]}>
          <Col xs={24} md={8}>
            <Card>
              <Statistic title="配置来源" value={rows.length} />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card>
              <Statistic title="已启用" value={rows.filter((row) => row.enabled).length} />
            </Card>
          </Col>
          <Col xs={24} md={8}>
            <Card>
              <Statistic
                title="已归属选题"
                value={rows.reduce((sum, row) => sum + row.collected_count, 0)}
              />
            </Card>
          </Col>
        </Row>
        <Alert
          type="info"
          showIcon
          title="停用保留历史资料；测试只预览，不写入题库。"
          description="来源地址仅支持公网 HTTP(S)。保存后可测试连接；修改名称或分类应用于后续采集，不会立即改写已有选题。"
        />
        <Input.Search
          aria-label="搜索来源"
          placeholder="搜索名称、分类或地址"
          allowClear
          onSearch={setQ}
          style={{ maxWidth: 380 }}
        />
        {resource.error && <Alert type="error" showIcon title={resource.error} />}
        <Card>
          <Table<ManagedSource>
            rowKey="id"
            loading={resource.loading}
            dataSource={rows.filter((row) =>
              `${row.name} ${row.category} ${row.display_category} ${row.url}`
                .toLowerCase()
                .includes(q.toLowerCase()),
            )}
            scroll={{ x: 1050 }}
            pagination={{ pageSize: 10, showSizeChanger: false }}
            columns={[
              {
                title: '采集接口',
                width: 290,
                render: (_, row) => (
                  <Space orientation="vertical" size={4}>
                    <Text strong>{row.name}</Text>
                    <a className="source-url" href={row.url} target="_blank" rel="noreferrer">
                      {row.url}
                    </a>
                    <Space wrap>
                      <Tag color="geekblue">{row.adapter}</Tag>
                      <Tag>{row.display_category}</Tag>
                      <Tag>{row.region}</Tag>
                      <Tag>{row.topic_kind}</Tag>
                    </Space>
                  </Space>
                ),
              },
              {
                title: '启用',
                width: 90,
                render: (_, row) => (
                  <Switch
                    aria-label={`启用来源：${row.name}`}
                    checked={row.enabled}
                    loading={busyId === row.id}
                    disabled={bulkBusy !== null}
                    onChange={async (enabled) => {
                      setBusyId(row.id);
                      try {
                        await write(`/knowledge/manage/sources/${row.id}`, 'PATCH', { enabled });
                        resource.refresh();
                      } catch (e) {
                        notice.error((e as Error).message);
                      } finally {
                        setBusyId(null);
                      }
                    }}
                  />
                ),
              },
              { title: '内容数量', dataIndex: 'collected_count', width: 100 },
              {
                title: '采集状态',
                width: 230,
                render: (_, row) => (
                  <Space orientation="vertical" size={4}>
                    <Tag
                      color={
                        !row.enabled
                          ? undefined
                          : row.status === 'success'
                            ? 'green'
                            : row.status === 'failed'
                              ? 'red'
                              : 'blue'
                      }
                    >
                      {!row.enabled
                        ? '已停用'
                        : row.status === 'success'
                          ? '最近采集成功'
                          : row.status === 'failed'
                            ? '最近采集失败'
                            : '等待采集'}
                    </Tag>
                    <Text type="secondary">最近成功：{formatTime(row.last_success)}</Text>
                    {row.error && <Text type="danger">{row.error}</Text>}
                  </Space>
                ),
              },
              {
                title: '最近测试',
                width: 210,
                render: (_, row) => (
                  <Space orientation="vertical" size={4}>
                    <Text>
                      {!row.last_test_at
                        ? '尚未测试'
                        : row.last_test_error
                          ? row.last_test_error
                          : row.last_test_count === null
                            ? '测试中，可稍后重试'
                            : `${row.last_test_count} 条可用条目`}
                    </Text>
                    <Text type="secondary">{formatTime(row.last_test_at)}</Text>
                  </Space>
                ),
              },
              {
                title: '操作',
                width: 180,
                render: (_, row) => (
                  <Space wrap>
                    <Button onClick={() => edit(row)}>编辑</Button>
                    <Button
                      loading={testing && previewSource?.id === row.id}
                      disabled={testing}
                      onClick={() => test(row)}
                    >
                      测试接口
                    </Button>
                    <Popconfirm
                      title="删除此采集接口？"
                      description="停止采集并移除配置，保留已入库选题。"
                      onConfirm={async () => {
                        try {
                          await write(`/knowledge/manage/sources/${row.id}`, 'DELETE');
                          resource.refresh();
                          notice.success('接口已删除，历史选题保留');
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
      <InterfaceFormModal
        open={open}
        editing={editing}
        options={options}
        onClose={() => setOpen(false)}
        onSaved={() => {
          setOpen(false);
          resource.refresh();
          notice.success('接口配置已保存，下一轮采集生效');
        }}
      />
      <InterfacePreviewModal
        source={previewSource}
        preview={preview}
        testing={testing}
        error={testError}
        onClose={() => setPreviewSource(null)}
      />
    </>
  );
}
