import { useAuth } from '../../app/auth';
import { UserMenu } from './UserMenu';
import {
  ApiOutlined,
  FireOutlined,
  GithubOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import { Button, Grid, Layout, Menu, Space, Tooltip, Typography } from 'antd';
import type { ReactNode } from 'react';
import { useState } from 'react';
import { navigationItems, viewLabels, type ViewKey } from '../../app/navigation';
const { Header, Sider, Content } = Layout;
const { Text } = Typography;
export function AppLayout({
  view,
  onNavigate,
  children,
}: {
  view: ViewKey;
  onNavigate: (view: ViewKey) => void;
  children: ReactNode;
}) {
  const { user } = useAuth();
  const screens = Grid.useBreakpoint();
  const [menuCollapsed, setMenuCollapsed] = useState<boolean | null>(null);
  const collapsed = menuCollapsed ?? !screens.lg;
  return (
    <Layout className="app-layout">
      <Sider
        width={224}
        collapsedWidth={72}
        collapsed={collapsed}
        className="app-sider"
        theme="dark"
      >
        <div className="brand">
          <div className="brand-icon">
            <FireOutlined />
          </div>
          {!collapsed && (
            <div>
              <strong>AIHot</strong>
              <span>Skills 热点资料库</span>
            </div>
          )}
        </div>
        {!collapsed && <div className="nav-label">工作空间</div>}
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[view]}
          defaultOpenKeys={['skills', 'knowledge-group', 'creator-center']}
          items={navigationItems?.filter((item) => item?.key !== 'creator-center' || !!user)}
          onClick={({ key }) => {
            onNavigate(key as ViewKey);
          }}
        />
        <Tooltip title={collapsed ? '展开菜单' : '收起菜单'} placement="right">
          <Button
            type="text"
            className="sider-toggle"
            aria-label={collapsed ? '展开菜单' : '收起菜单'}
            aria-expanded={!collapsed}
            icon={collapsed ? <MenuUnfoldOutlined /> : <MenuFoldOutlined />}
            onClick={() => setMenuCollapsed(!collapsed)}
          >
            {!collapsed && '收起菜单'}
          </Button>
        </Tooltip>
        <UserMenu collapsed={collapsed} onNavigate={onNavigate} />
      </Sider>
      <Layout className={collapsed ? 'main-layout collapsed' : 'main-layout'}>
        <Header className="app-header">
          <Space>
            <GithubOutlined />
            <Text type="secondary">创作资料库</Text>
            <Text type="secondary">/</Text>
            <Text>{viewLabels[view]}</Text>
          </Space>
          <Button icon={<ApiOutlined />} href="/docs" target="_blank">
            {screens.sm ? 'API 文档' : 'API'}
          </Button>
        </Header>
        <Content className="app-content">{children}</Content>
      </Layout>
    </Layout>
  );
}
