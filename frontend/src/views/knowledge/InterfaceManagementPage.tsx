import { PlusOutlined,ReloadOutlined } from "@ant-design/icons";
import {
Alert,
AutoComplete,
Button,
Card,
Col,
Flex,
Form,
Input,
InputNumber,
message,
Modal,
Popconfirm,
Row,
Select,
Space,
Spin,
Statistic,
Switch,
Table,
Tag,
Typography
} from "antd";
import { useState } from "react";
import { write } from '../../api/http';
import { useResource as useManagement } from '../../hooks/useResource';
import type { CategoryResponse,ManagedSource,Preview } from '../../types/knowledge-management';
import { formatTime } from '../../utils/date';
const {Title,Text,Paragraph}=Typography;
export function InterfaceManagementPage({ tick }: { tick: number }) {
  const resource = useManagement<{ items: ManagedSource[] }>('/knowledge/manage/sources', tick);
  const categories = useManagement<CategoryResponse>('/knowledge/manage/categories', tick);
  const [form] = Form.useForm<Omit<ManagedSource, 'id'> & { options_json: string }>();
  const [editing, setEditing] = useState<ManagedSource | null>(null);
  const [open, setOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
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
    setSaveError('');
    form.resetFields();
    form.setFieldsValue({
      ...{
        region: '国外' as const,
        topic_kind: '热点候选' as const,
        enabled: true,
        adapter: 'rss',
        item_limit: 100,
      },
      ...source,
      options_json: JSON.stringify(source?.options ?? {}, null, 2),
    });
    setOpen(true);
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
        <Space>
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
      <Modal
        title={editing ? '编辑采集接口' : '新增采集接口'}
        open={open}
        onCancel={() => setOpen(false)}
        confirmLoading={saving}
        okText="保存"
        cancelText="取消"
        onOk={async () => {
          try {
            const values = await form.validateFields();
            setSaving(true);
            setSaveError('');
            const body = {
              name: values.name.trim(),
              category: values.category.trim(),
              region: values.region,
              topic_kind: values.topic_kind,
              enabled: values.enabled,
              url: values.url.trim(),
              adapter: values.adapter,
              item_limit: values.item_limit,
              options: JSON.parse(values.options_json || '{}'),
            };
            await write(
              editing ? `/knowledge/manage/sources/${editing.id}` : '/knowledge/manage/sources',
              editing ? 'PATCH' : 'POST',
              body,
            );
            setOpen(false);
            resource.refresh();
            notice.success('来源配置已保存，下一轮采集生效');
          } catch (e) {
            if (e instanceof Error) setSaveError(e.message);
          } finally {
            setSaving(false);
          }
        }}
      >
        {saveError && (
          <Alert type="error" showIcon title={saveError} style={{ marginBottom: 16 }} />
        )}
        <Form form={form} layout="vertical">
          <Form.Item
            name="name"
            label="来源名称"
            rules={[{ required: true, whitespace: true, max: 200 }]}
          >
            <Input maxLength={200} />
          </Form.Item>
          <Form.Item
            name="url"
            label="请求地址"
            extra="填写公开 RSS / Atom 或 JSON API 地址；支持修改，历史选题保留。请勿在地址中填写私密凭证。"
            rules={[{ required: true, type: 'url', max: 2000 }]}
          >
            <Input placeholder="https://example.com/feed.xml" />
          </Form.Item>
          <Form.Item name="adapter" label="接口类型" rules={[{ required: true }]}>
            <Select
              options={[
                { value: 'rss', label: 'RSS / Atom（含 arXiv）' },
                { value: 'hackernews', label: 'Hacker News 官方 API' },
                { value: 'wikipedia', label: 'Wikipedia 历史事件 API' },
                { value: 'json', label: '通用 JSON GET API' },
              ]}
            />
          </Form.Item>
          <Form.Item name="item_limit" label="单次采集上限" rules={[{ required: true }]}>
            <InputNumber min={1} max={200} />
          </Form.Item>
          <Form.Item
            name="options_json"
            label="JSON 字段映射（其他类型保留 {}）"
            extra='例如 {"items_path":"data.items","title_field":"title","url_field":"url","summary_field":"description","date_field":"published_at"}，支持 data.0.title 点路径。'
            rules={[
              {
                validator: (_, value) => {
                  try {
                    const obj = JSON.parse(value || '{}');
                    if (
                      !obj ||
                      Array.isArray(obj) ||
                      typeof obj !== 'object' ||
                      Object.values(obj).some((v) => typeof v !== 'string')
                    )
                      throw new Error();
                    return Promise.resolve();
                  } catch {
                    return Promise.reject(new Error('请填写键值均为字符串的 JSON 对象'));
                  }
                },
              },
            ]}
          >
            <Input.TextArea rows={5} />
          </Form.Item>
          <Form.Item
            name="category"
            label="内容分类"
            rules={[{ required: true, whitespace: true, max: 50 }]}
          >
            <AutoComplete
              options={options}
              filterOption={(input, option) => String(option?.value).includes(input)}
              placeholder="选择或输入分类"
              maxLength={50}
            />
          </Form.Item>
          <Form.Item name="region" label="默认题材地区" rules={[{ required: true }]}>
            <Select options={['国内', '国外'].map((value) => ({ value, label: value }))} />
          </Form.Item>
          <Form.Item name="topic_kind" label="选题类型" rules={[{ required: true }]}>
            <Select options={['热点候选', '知识探索'].map((value) => ({ value, label: value }))} />
          </Form.Item>
          <Form.Item name="enabled" label="启用采集" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
      <Modal
        title={`接口测试 · ${previewSource?.name ?? ''}`}
        open={previewSource !== null}
        onCancel={() => setPreviewSource(null)}
        footer={<Button onClick={() => setPreviewSource(null)}>关闭</Button>}
        width={700}
      >
        <Spin spinning={testing}>
          <Space orientation="vertical" size={16} className="full-width">
            <Text type="secondary">仅预览前 5 条，不保存到题库。同一来源每 30 秒可测试一次。</Text>
            {testError && <Alert type="error" showIcon title={testError} />}
            {preview && (
              <>
                <Alert
                  type={preview.ok ? 'success' : 'error'}
                  showIcon
                  title={
                    preview.ok ? `读取成功，发现 ${preview.item_count} 条有效条目` : '来源测试失败'
                  }
                  description={preview.error}
                />
                {preview.items.map((item) => (
                  <Card key={item.url} size="small">
                    <a href={item.url} target="_blank" rel="noreferrer">
                      {item.title}
                    </a>
                    <div>
                      <Text type="secondary">{formatTime(item.published_at)}</Text>
                    </div>
                  </Card>
                ))}
              </>
            )}
          </Space>
        </Spin>
      </Modal>
    </>
  );
}
