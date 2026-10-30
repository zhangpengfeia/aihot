import { PlusOutlined,StarOutlined } from "@ant-design/icons";
import { Alert,Button,Input,Modal,Space,Switch,Typography,message } from "antd";
import { useState } from "react";
import { get,write } from '../../api/http';
import { type CreationCard,type PersonalItem } from '../../types/workspace';
export function PersonalButton({
  kind,
  targetId,
  onSaved,
}: {
  kind: 'repository' | 'topic';
  targetId: number;
  onSaved?: () => void;
}) {
  const [open, setOpen] = useState(false);
  const [item, setItem] = useState<PersonalItem | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, context] = message.useMessage();
  const path = `/workspace/items/${kind}/${targetId}`;
  async function load() {
    setOpen(true);
    setBusy(true);
    setError('');
    setItem(null);
    try {
      setItem(await get<PersonalItem>(path));
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  async function save() {
    if (!item) return;
    setBusy(true);
    setError('');
    try {
      await write(path, 'PUT', { favorite: item.favorite, note: item.note });
      setOpen(false);
      notice.success('收藏与备注已保存');
      onSaved?.();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <>
      {context}
      <Button icon={<StarOutlined />} onClick={load}>
        收藏 / 备注
      </Button>
      <Modal
        title="收藏与个人备注"
        open={open}
        onCancel={() => setOpen(false)}
        onOk={save}
        okText="保存"
        cancelText="取消"
        confirmLoading={busy}
        okButtonProps={{ disabled: !item }}
        destroyOnHidden
      >
        {error && (
          <Alert
            type="error"
            showIcon
            title={error}
            action={!item ? <Button onClick={load}>重试</Button> : undefined}
          />
        )}
        {item && (
          <Space orientation="vertical" className="full-width" size={16}>
            <Typography.Text strong>{item.title}</Typography.Text>
            <Space>
              <Switch
                checked={item.favorite}
                onChange={(favorite) => setItem({ ...item, favorite })}
              />
              收藏到我的资料
            </Space>
            <Input.TextArea
              aria-label="个人备注"
              value={item.note}
              rows={7}
              maxLength={10000}
              showCount
              placeholder="记录使用体验、安装问题或创作思路；取消收藏后仍保留备注。"
              onChange={(event) => setItem({ ...item, note: event.target.value })}
            />
          </Space>
        )}
      </Modal>
    </>
  );
}
export function AddToBoard({ topicId }: { topicId: number }) {
  const [busy, setBusy] = useState(false);
  const [notice, context] = message.useMessage();
  return (
    <>
      {context}
      <Button
        icon={<PlusOutlined />}
        loading={busy}
        onClick={async () => {
          setBusy(true);
          try {
            const card = await write<CreationCard>('/workspace/cards', 'POST', {
              topic_id: topicId,
            });
            notice.success(`已加入创作看板 · ${card.stage}`);
          } catch (e) {
            notice.error((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        加入创作看板
      </Button>
    </>
  );
}