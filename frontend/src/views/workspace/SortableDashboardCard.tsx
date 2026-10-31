import type { ReactNode } from 'react';
import { Button, Space, Tooltip } from 'antd';
import { ArrowDownOutlined, ArrowUpOutlined, HolderOutlined } from '@ant-design/icons';
import { useSortable } from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import { CARD_LABELS, type CardId } from '../../store/dashboardStore';
export function SortableDashboardCard({
  id,
  children,
  first,
  last,
  move,
}: {
  id: CardId;
  children: ReactNode;
  first: boolean;
  last: boolean;
  move: (direction: number) => void;
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    setActivatorNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });
  return (
    <section
      ref={setNodeRef}
      className={`dashboard-sortable-card ${id === 'new_entries' || id === 'risers' ? 'dashboard-half-card' : ''}`}
      style={{
        transform: CSS.Transform.toString(transform),
        transition,
        zIndex: isDragging ? 10 : undefined,
        opacity: isDragging ? 0.7 : 1,
      }}
      aria-label={CARD_LABELS[id]}
    >
      <div className="dashboard-sort-toolbar">
        <Space size={0}>
          <Tooltip title="上移">
            <Button
              type="text"
              size="small"
              aria-label={`上移${CARD_LABELS[id]}`}
              disabled={first}
              icon={<ArrowUpOutlined />}
              onClick={() => move(-1)}
            />
          </Tooltip>
          <Tooltip title="下移">
            <Button
              type="text"
              size="small"
              aria-label={`下移${CARD_LABELS[id]}`}
              disabled={last}
              icon={<ArrowDownOutlined />}
              onClick={() => move(1)}
            />
          </Tooltip>
          <Button
            ref={setActivatorNodeRef}
            {...attributes}
            {...listeners}
            className="dashboard-drag-handle"
            type="text"
            size="small"
            icon={<HolderOutlined />}
            aria-label={`拖动排序${CARD_LABELS[id]}`}
          >
            拖动排序
          </Button>
        </Space>
      </div>
      {children}
    </section>
  );
}
