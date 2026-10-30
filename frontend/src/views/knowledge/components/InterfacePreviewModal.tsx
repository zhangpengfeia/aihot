import { Alert, Button, Card, Modal, Space, Spin, Typography } from 'antd';
import type { ManagedSource, Preview } from '../../../types/knowledge-management';
import { formatTime } from '../../../utils/date';
const { Text } = Typography;
export function InterfacePreviewModal({
  source,
  preview,
  testing,
  error,
  onClose,
}: {
  source: ManagedSource | null;
  preview: Preview | null;
  testing: boolean;
  error: string;
  onClose: () => void;
}) {
  return (
    <Modal
      title={`接口测试 · ${source?.name ?? ''}`}
      open={source !== null}
      onCancel={onClose}
      footer={<Button onClick={onClose}>关闭</Button>}
      width={700}
    >
      <Spin spinning={testing}>
        <Space orientation="vertical" size={16} className="full-width">
          <Text type="secondary">仅预览前 5 条，不保存到题库。同一来源每 30 秒可测试一次。</Text>
          {error && <Alert type="error" showIcon title={error} />}
          {preview && (
            <>
              <Alert
                type={preview.ok ? 'success' : 'error'}
                showIcon
                title={
                  preview.ok ? `读取成功，发现 ${preview.item_count} 条有效条目` : '来源测试失败'
                }
                description={preview.error}
              />
              {preview.items.map((item) => (
                <Card key={item.url} size="small">
                  <a href={item.url} target="_blank" rel="noreferrer">
                    {item.title}
                  </a>
                  <div>
                    <Text type="secondary">{formatTime(item.published_at)}</Text>
                  </div>
                </Card>
              ))}
            </>
          )}
        </Space>
      </Spin>
    </Modal>
  );
}
