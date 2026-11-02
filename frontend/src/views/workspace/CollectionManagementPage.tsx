import { ApiOutlined, ClockCircleOutlined } from '@ant-design/icons';
import { Tabs } from 'antd';
import { useState } from 'react';
import { PageActivityContext, usePageActive } from '../../app/pageActivity';
import { useRefreshTick } from '../../hooks/useRefreshTick';
import { InterfacesPage } from '../knowledge/InterfacesPage';
import { CollectionStatusPage } from './CollectionStatusPage';

type CollectionTab = 'status' | 'interfaces';
function CollectionPane({ kind }: { kind: CollectionTab }) {
  const { tick } = useRefreshTick();
  return kind === 'status' ? <CollectionStatusPage tick={tick} /> : <InterfacesPage tick={tick} />;
}

export function CollectionManagementPage() {
  const [tab, setTab] = useState<CollectionTab>('status');
  const pageActive = usePageActive();
  return (
    <Tabs
      activeKey={tab}
      onChange={(key) => setTab(key as CollectionTab)}
      items={[
        { key: 'status' as const, label: '采集状态面板', icon: <ClockCircleOutlined /> },
        { key: 'interfaces' as const, label: '采集接口管理', icon: <ApiOutlined /> },
      ].map((item) => ({
        ...item,
        children: (
          <PageActivityContext.Provider value={pageActive && tab === item.key}>
            <CollectionPane kind={item.key} />
          </PageActivityContext.Provider>
        ),
      }))}
    />
  );
}
