import { useState } from 'react';
import { PageHeading } from '../components/common/PageHeading';
import { AppLayout } from '../components/layout/AppLayout';
import { useRefreshTick } from '../hooks/useRefreshTick';
import { CategoryManagementPage } from '../views/knowledge/CategoryManagementPage';
import { InterfacesPage } from '../views/knowledge/InterfacesPage';
import KnowledgePage from '../views/knowledge/KnowledgeLibraryPage';
import SkillLibrary from '../views/skills/SkillLibraryPage';
import { SkillRankingPage } from '../views/skills/SkillRankingPage';
import { SkillDetailDrawer } from '../views/skills/components/SkillDetailDrawer';
import { CollectionStatusPage } from '../views/workspace/CollectionStatusPage';
import { CreationBoardPage } from '../views/workspace/CreationBoardPage';
import { DailySummaryPage } from '../views/workspace/DailySummaryPage';
import { FavoritesPage } from '../views/workspace/FavoritesPage';
import type { ViewKey } from './navigation';

/** 应用仅管理导航和全局资料抽屉，具体页面自行管理查询与表单。 */
export default function App(){
 const [view,setView]=useState<ViewKey>('library');
 const [selected,setSelected]=useState<number|null>(null);
 const {tick,refresh}=useRefreshTick();
 let content;
 switch(view){
 case 'knowledge':content=<KnowledgePage/>;break;
 case 'sources':content=<InterfacesPage tick={tick}/>;break;
 case 'categories':content=<CategoryManagementPage tick={tick}/>;break;
 case 'favorites':content=<FavoritesPage tick={tick} onSelect={setSelected}/>;break;
 case 'summary':content=<DailySummaryPage tick={tick} onSelect={setSelected}/>;break;
 case 'status':content=<CollectionStatusPage tick={tick}/>;break;
 case 'creation':content=<CreationBoardPage tick={tick}/>;break;
 case 'today':case 'history':content=<SkillRankingPage history={view==='history'} tick={tick} onRefresh={refresh} onSelect={setSelected}/>;break;
 default:content=<><PageHeading title='Skill 库' description='按创作用途整理项目，保留安装说明与许可证。' refresh={refresh} loading={false}/><SkillLibrary tick={tick} onSelect={setSelected}/></>;
 }
 return <AppLayout view={view} onNavigate={setView}>{content}<SkillDetailDrawer selected={selected} onClose={()=>setSelected(null)}/></AppLayout>;
}
