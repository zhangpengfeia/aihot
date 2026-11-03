import { Alert, AutoComplete, Form, Input, InputNumber, Modal, Select, Switch } from 'antd';
import { useEffect, useState } from 'react';
import { write } from '../../../api/http';
import type { ManagedSource } from '../../../types/knowledge-management';
export function InterfaceFormModal({
  open,
  editing,
  options,
  onClose,
  onSaved,
}: {
  open: boolean;
  editing: ManagedSource | null;
  options: { value: string }[];
  onClose: () => void;
  onSaved: () => void;
}) {
  const [form] = Form.useForm<Omit<ManagedSource, 'id'> & { options_json: string }>();
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState('');
  useEffect(() => {
    if (!open) return;
    const source = editing;
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
  }, [open, editing, form]);
  return (
    <Modal
      title={editing ? '编辑采集接口' : '新增采集接口'}
      open={open}
      onCancel={onClose}
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
          onSaved();
        } catch (e) {
          if (e instanceof Error) setSaveError(e.message);
        } finally {
          setSaving(false);
        }
      }}
    >
      {saveError && <Alert type="error" showIcon title={saveError} style={{ marginBottom: 16 }} />}
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
              { value: 'hotlist', label: '热搜榜单（聚合接口 / 字段映射）' },
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
  );
}
