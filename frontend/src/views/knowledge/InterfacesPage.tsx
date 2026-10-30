import { Tabs } from 'antd';
import { CategoryManagementPage } from './CategoryManagementPage';
import { InterfaceManagementPage } from './InterfaceManagementPage';
/** 同一个管理入口下分别维护采集接口和分类，避免重复导航。 */
export function InterfacesPage({ tick }: { tick: number }) {
  return (
    <Tabs
      defaultActiveKey="interfaces"
      items={[
        { key: 'interfaces', label: '采集接口', children: <InterfaceManagementPage tick={tick} /> },
        { key: 'categories', label: '分类整理', children: <CategoryManagementPage tick={tick} /> },
      ]}
    />
  );
}
