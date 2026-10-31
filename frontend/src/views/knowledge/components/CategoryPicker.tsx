import type { Meta } from '../../../types/knowledge';
import { GroupedFilterPicker } from '../../../components/common/GroupedFilterPicker';
export function CategoryPicker({
  meta,
  value,
  onChange,
}: {
  meta: Meta;
  value: string[];
  onChange: (labels: string[]) => void;
}) {
  return (
    <GroupedFilterPicker
      title="选择内容分类与标签"
      placeholder="选择内容分类 / 热门与小众标签"
      summaryLabel="内容分类"
      allLabel="全部分类与标签"
      searchPlaceholder="搜索分类或标签，如：历史、配音、冷知识"
      noun="标签"
      value={value}
      onChange={onChange}
      groups={[
        {
          key: 'existing',
          name: '已有内容分类',
          options: [...new Set(meta.categories)].map((tag) => ({ value: tag, label: tag })),
        },
        ...Object.entries(meta.tag_groups ?? {}).map(([name, tags], index) => ({
          key: `group-${index}`,
          name,
          options: [...new Set(tags)].map((tag) => ({ value: tag, label: tag })),
        })),
      ]}
    />
  );
}
