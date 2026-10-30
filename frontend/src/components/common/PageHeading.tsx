import { ReloadOutlined } from "@ant-design/icons";
import {
Button,
Flex,
Typography
} from "antd";
const {Title,Text,Paragraph}=Typography;
export function PageHeading({
  title,
  description,
  refresh,
  loading,
}: {
  title: string;
  description: string;
  refresh: () => void;
  loading: boolean;
}) {
  return (
    <Flex justify="space-between" align="center" wrap gap={16} className="page-heading">
      <div>
        <Title level={2}>{title}</Title>
        <Paragraph type="secondary">{description}</Paragraph>
      </div>
      <Button icon={<ReloadOutlined />} onClick={refresh} loading={loading}>
        刷新数据
      </Button>
    </Flex>
  );
}
