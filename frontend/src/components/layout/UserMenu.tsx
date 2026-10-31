import { useState } from 'react';
import { Avatar, Button, Dropdown, Form, Input, Modal, message } from 'antd';
import {
  ApiOutlined,
  ClockCircleOutlined,
  LoginOutlined,
  LogoutOutlined,
  TeamOutlined,
  UserOutlined,
} from '@ant-design/icons';
import { useAuth } from '../../app/auth';
import { write } from '../../api/http';
import type { ViewKey } from '../../app/navigation';
export function UserMenu({
  collapsed,
  onNavigate,
}: {
  collapsed: boolean;
  onNavigate: (v: ViewKey) => void;
}) {
  const { user, refresh } = useAuth();
  const [login, setLogin] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form] = Form.useForm();
  return (
    <>
      <Dropdown
        trigger={['click']}
        placement="topLeft"
        menu={{
          items: [
            {
              key: 'profile',
              label: user
                ? `${user.display_name} · ${user.role === 'admin' ? '管理员' : '用户'}`
                : '访客 · 公开浏览',
              disabled: true,
            },
            { type: 'divider' },
            {
              key: 'status',
              icon: <ClockCircleOutlined />,
              label: '采集状态面板',
              onClick: () => onNavigate('status'),
            },
            ...(user?.role === 'admin'
              ? [
                  {
                    key: 'sources',
                    icon: <ApiOutlined />,
                    label: '采集接口管理',
                    onClick: () => onNavigate('sources'),
                  },
                  {
                    key: 'users',
                    icon: <TeamOutlined />,
                    label: '用户管理',
                    onClick: () => onNavigate('users'),
                  },
                ]
              : []),
            { type: 'divider' },
            {
              key: 'auth',
              icon: user ? <LogoutOutlined /> : <LoginOutlined />,
              label: user ? '退出登录' : '账号登录',
              onClick: async () => {
                if (!user) {
                  setLogin(true);
                  return;
                }
                try {
                  await write('/auth/logout', 'POST', {});
                  refresh();
                  onNavigate('summary');
                } catch (e) {
                  message.error((e as Error).message);
                }
              },
            },
          ],
        }}
      >
        <button className="user-menu-button" aria-label="用户设置菜单">
          <Avatar icon={<UserOutlined />} style={{ background: '#4263eb', flexShrink: 0 }} />
          {!collapsed && (
            <>
              <span>
                <strong>{user?.display_name ?? '访客'}</strong>
                <small>
                  {user ? (user.role === 'admin' ? '管理员' : '用户') : '公开浏览 · 点击登录'}
                </small>
              </span>
              <span>···</span>
            </>
          )}
        </button>
      </Dropdown>
      <Modal
        title="账号登录"
        open={login}
        footer={null}
        onCancel={() => setLogin(false)}
        destroyOnHidden
      >
        <Form
          form={form}
          layout="vertical"
          onFinish={async (values) => {
            setLoading(true);
            try {
              await write('/auth/login', 'POST', values);
              setLogin(false);
              form.resetFields();
              onNavigate('summary');
              refresh();
            } catch (e) {
              message.error((e as Error).message);
            } finally {
              setLoading(false);
            }
          }}
        >
          <Form.Item name="username" label="用户名" rules={[{ required: true }]}>
            <Input autoComplete="username" />
          </Form.Item>
          <Form.Item name="password" label="密码" rules={[{ required: true }]}>
            <Input.Password autoComplete="current-password" />
          </Form.Item>
          <Button type="primary" htmlType="submit" loading={loading} block>
            登录
          </Button>
        </Form>
      </Modal>
    </>
  );
}
