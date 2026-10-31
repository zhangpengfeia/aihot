import { useAuth } from './auth';
import { HotListsPage } from '../views/knowledge/HotListsPage';
import { Alert } from 'antd';
import { UserManagementPage } from '../views/users/UserManagementPage';
import { useState } from 'react';
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

/** 应用仅管理导航和全局资料抽屉，具体页面自行管理查询与表单。 */
export default function App() {
  const { user } = useAuth();
  const [view, setView] = useState<ViewKey>('summary');
  const [selected, setSelected] = useState<number | null>(null);
  const { tick, refresh } = useRefreshTick();
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
      content = <FavoritesPage tick={tick} onSelect={setSelected} />;
      break;
    case 'summary':
      content = <DailySummaryPage tick={tick} onSelect={setSelected} />;
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
          onSelect={setSelected}
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
          <SkillLibraryPage tick={tick} onSelect={setSelected} />
        </>
      );
  }
  return (
    <AppLayout view={view} onNavigate={setView}>
      {['sources', 'categories', 'users'].includes(view) && user?.role !== 'admin' ? (
        <Alert type="warning" showIcon title="此页面仅限管理员访问" />
      ) : ['favorites', 'creation'].includes(view) && !user ? (
        <Alert type="info" title="请点击左下角头像登录后访问自己的创作者中心" />
      ) : (
        content
      )}
      <SkillDetailDrawer selected={selected} onClose={() => setSelected(null)} />
    </AppLayout>
  );
}
