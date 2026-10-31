import { ReloadOutlined } from '@ant-design/icons';
import type { ReactNode } from 'react';
import { Button, Flex, Space, Typography } from 'antd';
const { Title, Paragraph } = Typography;
export function PageHeading({
  title,
  description,
  refresh,
  loading,
  actions,
}: {
  title: string;
  description: string;
  refresh: () => void;
  loading: boolean;
  actions?: ReactNode;
}) {
  return (
    <Flex justify="space-between" align="center" wrap gap={16} className="page-heading">
      <div>
        <Title level={2}>{title}</Title>
        <Paragraph type="secondary">{description}</Paragraph>
      </div>
      <Space wrap>
        {actions}
        <Button icon={<ReloadOutlined />} onClick={refresh} loading={loading}>
          刷新数据
        </Button>
      </Space>
    </Flex>
  );
}
