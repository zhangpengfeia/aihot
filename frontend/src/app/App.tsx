import { useAuth } from './auth';
import { HotListsPage } from '../views/knowledge/HotListsPage';
import { Alert } from 'antd';
import { UserManagementPage } from '../views/users/UserManagementPage';
import { useRef, useState } from 'react';
import { ConfigProvider } from 'antd';
import { PageActivityContext } from './pageActivity';
import { closeTab, initialTabs, openTab } from './workspaceTabs';
import { PageHeading } from '../components/common/PageHeading';
import { AppLayout } from '../components/layout/AppLayout';
import { useRefreshTick } from '../hooks/useRefreshTick';
import { CategoryManagementPage } from '../views/knowledge/CategoryManagementPage';
import { InterfacesPage } from '../views/knowledge/InterfacesPage';
import KnowledgeLibraryPage from '../views/knowledge/KnowledgeLibraryPage';
import SkillLibraryPage from '../views/skills/SkillLibraryPage';
import { SkillRankingPage } from '../views/skills/SkillRankingPage';
import { SkillDetailDrawer } from '../views/skills/components/SkillDetailDrawer';
import { CollectionStatusPage } from '../views/workspace/CollectionStatusPage';
import { CreationBoardPage } from '../views/workspace/CreationBoardPage';
import { DailySummaryPage } from '../views/workspace/DailySummaryPage';
import { FavoritesPage } from '../views/workspace/FavoritesPage';
import type { ViewKey } from './navigation';

/** 账号切换后释放所有页面缓存，避免保留上一账号的个人资料。 */
export default function App() {
  const { user } = useAuth();
  return <Workspace key={`${user?.id ?? 'guest'}:${user?.role ?? 'guest'}`} />;
}
function Workspace() {
  const [tabs, setTabs] = useState(initialTabs);
  const [selected, setSelected] = useState<number | null>(null);
  return (
    <AppLayout
      view={tabs.active}
      onNavigate={(key) => setTabs((state) => openTab(state, key))}
      tabs={tabs.opened}
      onCloseTab={(key) => setTabs((state) => closeTab(state, key))}
    >
      {tabs.opened.map((key) => (
        <CachedPage key={key} view={key} active={key === tabs.active} onSelect={setSelected} />
      ))}
      <SkillDetailDrawer selected={selected} onClose={() => setSelected(null)} />
    </AppLayout>
  );
}
function CachedPage({
  view,
  active,
  onSelect,
}: {
  view: ViewKey;
  active: boolean;
  onSelect: (id: number) => void;
}) {
  const container = useRef<HTMLDivElement>(null);
  return (
    <div ref={container} hidden={!active}>
      <PageActivityContext.Provider value={active}>
        <ConfigProvider getPopupContainer={() => container.current ?? document.body}>
          <PageContent view={view} onSelect={onSelect} />
        </ConfigProvider>
      </PageActivityContext.Provider>
    </div>
  );
}
function PageContent({ view, onSelect }: { view: ViewKey; onSelect: (id: number) => void }) {
  const { user } = useAuth();
  const { tick, refresh } = useRefreshTick(
    view === 'today' ? 15 * 60_000 : view === 'history' ? null : 60_000,
  );
  let content;
  switch (view) {
    case 'hotlists':
      content = <HotListsPage tick={tick} />;
      break;
    case 'users':
      content = <UserManagementPage />;
      break;
    case 'knowledge':
      content = <KnowledgeLibraryPage />;
      break;
    case 'sources':
      content = <InterfacesPage tick={tick} />;
      break;
    case 'categories':
      content = <CategoryManagementPage tick={tick} />;
      break;
    case 'favorites':
      content = <FavoritesPage tick={tick} onSelect={onSelect} />;
      break;
    case 'summary':
      content = <DailySummaryPage tick={tick} onSelect={onSelect} />;
      break;
    case 'status':
      content = <CollectionStatusPage tick={tick} />;
      break;
    case 'creation':
      content = <CreationBoardPage tick={tick} />;
      break;
    case 'today':
    case 'history':
      content = (
        <SkillRankingPage
          key={view}
          history={view === 'history'}
          tick={tick}
          onRefresh={refresh}
          onSelect={onSelect}
        />
      );
      break;
    default:
      content = (
        <>
          <PageHeading
            title="AI 项目库"
            description="按创作用途整理项目，保留安装说明与许可证。"
            refresh={refresh}
            loading={false}
          />
          <SkillLibraryPage tick={tick} onSelect={onSelect} />
        </>
      );
  }
  return ['sources', 'categories', 'users', 'status'].includes(view) && user?.role !== 'admin' ? (
    <Alert type="warning" showIcon title="此页面仅限管理员访问" />
  ) : ['favorites', 'creation'].includes(view) && !user ? (
    <Alert type="info" title="请点击左下角头像登录后访问自己的创作者中心" />
  ) : (
    content
  );
}
