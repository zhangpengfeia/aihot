import type { ReactNode } from 'react';
import { Button, Space, Tooltip } from 'antd';
import { CloseOutlined, HolderOutlined } from '@ant-design/icons';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { CARD_LABELS, type CardId } from '../../store/dashboardStore';
export function SortableDashboardCard({
  id,
  children,
  editing,
  onRemove,
}: {
  id: CardId;
  children: ReactNode;
  editing: boolean;
  onRemove: () => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id, disabled: !editing });
  return (
    <section
      ref={setNodeRef}
      className={`dashboard-sortable-card ${editing ? 'dashboard-editing' : ''} ${id === 'new_entries' || id === 'risers' ? 'dashboard-half-card' : ''}`}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        zIndex: isDragging ? 10 : undefined,
        opacity: isDragging ? 0.7 : 1,
      }}
      aria-label={CARD_LABELS[id]}
    >
      {editing && (
        <div className="dashboard-sort-toolbar">
          <Space size={0}>
            <Tooltip title="拖拽排序（支持键盘空格和方向键）">
              <Button
                ref={setActivatorNodeRef}
                {...attributes}
                {...listeners}
                className="dashboard-drag-handle"
                type="text"
                size="small"
                icon={<HolderOutlined />}
                aria-label={`拖动排序${CARD_LABELS[id]}`}
              />
            </Tooltip>
            <Tooltip title="移除卡片">
              <Button
                type="text"
                size="small"
                icon={<CloseOutlined />}
                aria-label={`移除${CARD_LABELS[id]}`}
                onClick={onRemove}
              />
            </Tooltip>
          </Space>
        </div>
      )}
      {children}
    </section>
  );
}
