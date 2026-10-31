import { useState } from 'react';
import {
  Alert,
  Button,
  Form,
  Input,
  Modal,
  Select,
  Space,
  Switch,
  Table,
  Tag,
  message,
} from 'antd';
import { write } from '../../api/http';
import { useResource } from '../../hooks/useResource';
export interface User {
  id: number;
  username: string;
  display_name: string;
  role: string;
  enabled: boolean;
}
export function UserManagementPage() {
  const [tick, setTick] = useState(0);
  const resource = useResource<User[]>('/admin/users', tick);
  const [editing, setEditing] = useState<User | null | undefined>(undefined);
  const [saving, setSaving] = useState(false);
  const [form] = Form.useForm();
  const open = (user: User | null) => {
    setEditing(user);
    form.resetFields();
    form.setFieldsValue(user ?? { role: 'user', enabled: true });
  };
  return (
    <Space orientation="vertical" className="full-width" size={20}>
      <h1>用户管理</h1>
      <Alert
        type="info"
        title="网站公开浏览；登录后可使用工作空间，管理员可管理用户、配置来源和手动采集。"
      />
      {resource.error && <Alert type="error" title={resource.error} />}
      <Button type="primary" onClick={() => open(null)}>
        新增用户
      </Button>
      <Table<User>
        rowKey="id"
        loading={resource.loading}
        dataSource={resource.data ?? []}
        columns={[
          { title: '用户名', dataIndex: 'username' },
          { title: '显示名称', dataIndex: 'display_name' },
          {
            title: '角色',
            dataIndex: 'role',
            render: (v) => <Tag>{v === 'admin' ? '管理员' : '用户'}</Tag>,
          },
          { title: '状态', dataIndex: 'enabled', render: (v) => (v ? '正常' : '已停用') },
          { title: '操作', render: (_, u) => <Button onClick={() => open(u)}>编辑</Button> },
        ]}
      />
      <Modal
        title={editing ? '编辑用户' : '新增用户'}
        open={editing !== undefined}
        confirmLoading={saving}
        onCancel={() => setEditing(undefined)}
        onOk={() => form.submit()}
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={async (values) => {
            setSaving(true);
            try {
              await write(
                editing ? `/admin/users/${editing.id}` : '/admin/users',
                editing ? 'PUT' : 'POST',
                values,
              );
              setEditing(undefined);
              setTick((t) => t + 1);
              message.success('用户已保存；修改账号后需重新登录');
            } catch (e) {
              message.error((e as Error).message);
            } finally {
              setSaving(false);
            }
          }}
        >
          <Form.Item
            name="username"
            label="用户名"
            rules={[
              { required: true },
              { pattern: /^[a-zA-Z0-9_.-]{1,80}$/, message: '仅限字母、数字、点、下划线和短横线' },
            ]}
          >
            <Input autoComplete="off" />
          </Form.Item>
          <Form.Item name="display_name" label="显示名称" rules={[{ required: true }]}>
            <Input maxLength={80} />
          </Form.Item>
          <Form.Item
            name="password"
            label={editing ? '重置密码（留空保留）' : '密码'}
            rules={[{ required: !editing }, { min: 12, message: '至少 12 位' }]}
          >
            <Input.Password autoComplete="new-password" />
          </Form.Item>
          <Form.Item name="role" label="角色">
            <Select
              options={[
                { value: 'user', label: '用户' },
                { value: 'admin', label: '管理员' },
              ]}
            />
          </Form.Item>
          <Form.Item name="enabled" label="启用" valuePropName="checked">
            <Switch />
          </Form.Item>
        </Form>
      </Modal>
    </Space>
  );
}
