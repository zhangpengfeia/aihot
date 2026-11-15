import { useAuth } from '../../app/auth';
import { UserMenu } from './UserMenu';
import {
  ApiOutlined,
  FireOutlined,
  GithubOutlined,
  MenuFoldOutlined,
  MenuUnfoldOutlined,
} from '@ant-design/icons';
import { Button, Dropdown, Grid, Layout, Menu, Space, Tabs, Tooltip, Typography } from 'antd';
import type { ReactNode } from 'react';
import { useLayoutEffect, useRef, useState } from 'react';
import { navigationItems, viewLabels, type ViewKey } from '../../app/navigation';
import { useMobileLayout } from '../../hooks/useMobileLayout';
const { Header, Sider, Content } = Layout;
const { Text } = Typography;
export function AppLayout({
  view,
  onNavigate,
  children,
  tabs,
  onCloseTab,
}: {
  view: ViewKey;
  onNavigate: (view: ViewKey) => void;
  children: ReactNode;
  tabs: ViewKey[];
  onCloseTab: (key: ViewKey) => void;
}) {
  const { user } = useAuth();
  const mobile = useMobileLayout();
  const screens = Grid.useBreakpoint();
  const [menuCollapsed, setMenuCollapsed] = useState<boolean | null>(null);
  const [openMenu, setOpenMenu] = useState<string | null>(null);
  const collapsed = menuCollapsed ?? !screens.lg;
  const scrollPositions = useRef(new Map<ViewKey, number>());
  const previousView = useRef(view);
  const menuItems = navigationItems.filter((item) => item.key !== 'creator-center' || !!user);

  useLayoutEffect(() => {
    if (mobile && previousView.current !== view) {
      window.scrollTo(0, scrollPositions.current.get(view) ?? 0);
    }
    previousView.current = view;
  }, [mobile, view]);

  function navigate(key: ViewKey) {
    if (mobile && key !== view) scrollPositions.current.set(view, window.scrollY);
    onNavigate(key);
  }

  return (
    <Layout className="app-layout">
      {!mobile && (
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
                <strong>张鹏飞的私人工作台</strong>
                <span>AI 热门项目资料库</span>
              </div>
            )}
          </div>
          {!collapsed && <div className="nav-label">工作空间</div>}
          <Menu
            theme="dark"
            mode="inline"
            selectedKeys={[view]}
            defaultOpenKeys={['skills', 'knowledge-group', 'creator-center']}
            items={menuItems}
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
          <UserMenu collapsed={collapsed} onNavigate={navigate} />
        </Sider>
      )}
      <Layout className={collapsed ? 'main-layout collapsed' : 'main-layout'}>
        <Header className="app-header">
          {mobile ? (
            <Text strong>张鹏飞的私人工作台</Text>
          ) : (
            <Space>
              <GithubOutlined />
              <Text type="secondary">创作资料库</Text>
              <Text type="secondary">/</Text>
              <Text>{viewLabels[view]}</Text>
            </Space>
          )}
          <Button icon={<ApiOutlined />} href="/docs" target="_blank">
            {screens.sm ? 'API 文档' : 'API'}
          </Button>
        </Header>
        <div className="workspace-tabs">
          <Tabs
            type="editable-card"
            hideAdd
            activeKey={view}
            onChange={(key) => navigate(key as ViewKey)}
            onEdit={(key, action) => {
              if (action === 'remove') {
                scrollPositions.current.delete(key as ViewKey);
                onCloseTab(key as ViewKey);
              }
            }}
            items={tabs.map((key) => ({
              key,
              label: viewLabels[key].split(' / ').pop(),
              closable: key !== 'summary',
            }))}
          />
        </div>
        <Content className="app-content">{children}</Content>
      </Layout>
      {mobile && (
        <nav className="mobile-nav" aria-label="主导航">
          {menuItems.map((item) =>
            'children' in item && item.children ? (
              <Dropdown
                key={item.key}
                trigger={['click']}
                placement="top"
                classNames={{ root: 'mobile-nav-popup' }}
                open={openMenu === item.key}
                onOpenChange={(open) =>
                  setOpenMenu((current) =>
                    open ? item.key : current === item.key ? null : current,
                  )
                }
                menu={{
                  items: item.children,
                  selectable: true,
                  selectedKeys: [view],
                  onClick: ({ key }) => {
                    setOpenMenu(null);
                    navigate(key as ViewKey);
                  },
                }}
              >
                <button
                  type="button"
                  className="mobile-nav-button"
                  aria-haspopup="menu"
                  aria-expanded={openMenu === item.key}
                  data-active={item.children.some((child) => child.key === view)}
                >
                  {item.icon}
                  <span>{item.label}</span>
                </button>
              </Dropdown>
            ) : (
              <button
                key={item.key}
                type="button"
                className="mobile-nav-button"
                aria-current={view === 'summary' ? 'page' : undefined}
                data-active={view === 'summary'}
                onClick={() => navigate('summary')}
              >
                {item.icon}
                <span>首页</span>
              </button>
            ),
          )}
          <UserMenu
            mobile
            collapsed={false}
            active={view === 'users' || view === 'collection' || view === 'categories'}
            onNavigate={navigate}
          />
        </nav>
      )}
    </Layout>
  );
}
