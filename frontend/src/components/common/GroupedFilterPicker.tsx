import { AppstoreOutlined, CheckOutlined } from '@ant-design/icons';
import { Button, Empty, Flex, Input, Modal, Select, Typography } from 'antd';
import { useEffect, useRef, useState } from 'react';
import './grouped-filter-picker.css';
export interface FilterOption {
  value: string;
  label: string;
  searchText?: string;
}
export interface FilterGroup {
  key: string;
  name: string;
  options: FilterOption[];
}
export function GroupedFilterPicker({
  groups,
  value,
  onChange,
  title,
  placeholder,
  summaryLabel,
  allLabel,
  searchPlaceholder,
  noun = '项',
}: {
  groups: FilterGroup[];
  value: string[];
  onChange: (values: string[]) => void;
  title: string;
  placeholder: string;
  summaryLabel: string;
  allLabel: string;
  searchPlaceholder: string;
  noun?: string;
}) {
  const [open, setOpen] = useState(false);
  const [draft, setDraft] = useState<string[]>([]);
  const [query, setQuery] = useState('');
  const [group, setGroup] = useState('all');
  const listRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (listRef.current) listRef.current.scrollTop = 0;
  }, [query, group, open]);
  const all = [
    ...new Map(
      groups.flatMap((item) => item.options).map((option) => [option.value, option]),
    ).values(),
  ];
  const byValue = new Map(all.map((option) => [option.value, option]));
  const options =
    group === 'selected'
      ? draft.map((id) => byValue.get(id) ?? { value: id, label: id })
      : group === 'all'
        ? all
        : (groups.find((item) => item.key === group)?.options ?? []);
  const filtered = options.filter((option) =>
    `${option.label} ${option.searchText ?? ''}`.toLowerCase().includes(query.trim().toLowerCase()),
  );
  return (
    <>
      <Button
        icon={<AppstoreOutlined />}
        className="grouped-filter-picker-trigger"
        onClick={() => {
          setDraft([...value]);
          setQuery('');
          setGroup('all');
          setOpen(true);
        }}
      >
        <span className="grouped-filter-picker-summary">
          {value.length
            ? `${summaryLabel}：${value
                .slice(0, 2)
                .map((id) => byValue.get(id)?.label ?? id)
                .join('、')}${value.length > 2 ? '…' : ''}`
            : placeholder}
        </span>
        {value.length > 0 && <Typography.Text type="secondary">{value.length} 项</Typography.Text>}
      </Button>
      <Modal
        title={title}
        open={open}
        width={880}
        onCancel={() => setOpen(false)}
        footer={
          <Flex justify="space-between" align="center" gap={12} wrap>
            <Flex align="center" gap={8}>
              <Button
                type="link"
                onClick={() => {
                  setGroup('selected');
                  setQuery('');
                }}
              >
                已选 {draft.length} 项
              </Button>
              <Button disabled={!draft.length} onClick={() => setDraft([])}>
                清空
              </Button>
            </Flex>
            <Flex gap={8}>
              <Button onClick={() => setOpen(false)}>取消</Button>
              <Button
                type="primary"
                onClick={() => {
                  onChange(draft);
                  setOpen(false);
                }}
              >
                应用筛选
              </Button>
            </Flex>
          </Flex>
        }
      >
        <Flex orientation="vertical" gap={16}>
          <Typography.Text type="secondary">
            按分组浏览或搜索，可多选，点击“应用筛选”生效。
          </Typography.Text>
          <Input.Search
            aria-label={searchPlaceholder}
            placeholder={searchPlaceholder}
            allowClear
            value={query}
            onChange={(event) => {
              setQuery(event.target.value);
              setGroup('all');
            }}
          />
          <Flex justify="space-between" align="center" gap={12} wrap>
            <Select
              aria-label={`${summaryLabel}分组`}
              value={group}
              style={{ width: 260, maxWidth: '100%' }}
              onChange={setGroup}
              options={[
                { value: 'all', label: `${allLabel}（${all.length}）` },
                { value: 'selected', label: `已选择（${draft.length}）` },
                ...groups
                  .filter((item) => item.options.length)
                  .map((item) => ({
                    value: item.key,
                    label: `${item.name}（${item.options.length}）`,
                  })),
              ]}
            />
            <Typography.Text type="secondary">
              {filtered.length} 个{query ? '搜索结果' : noun}
            </Typography.Text>
          </Flex>
          <div
            ref={listRef}
            className="grouped-filter-picker-options"
            role="region"
            aria-label={`可滚动的${noun}列表`}
            tabIndex={0}
          >
            {filtered.map((option) => (
              <Button
                key={option.value}
                title={option.label}
                aria-pressed={draft.includes(option.value)}
                type={draft.includes(option.value) ? 'primary' : 'default'}
                icon={draft.includes(option.value) ? <CheckOutlined /> : undefined}
                onClick={() =>
                  setDraft((previous) =>
                    previous.includes(option.value)
                      ? previous.filter((id) => id !== option.value)
                      : [...previous, option.value],
                  )
                }
              >
                {option.label}
              </Button>
            ))}
            {!filtered.length && (
              <div className="grouped-filter-picker-empty">
                <Empty
                  image={Empty.PRESENTED_IMAGE_SIMPLE}
                  description={group === 'selected' ? '尚未选择' : '没有匹配结果，试试其他关键词'}
                />
              </div>
            )}
          </div>
        </Flex>
      </Modal>
    </>
  );
}
