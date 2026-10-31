import { GroupedFilterPicker } from '../../../components/common/GroupedFilterPicker';
import type { HotPlatform } from '../../../types/hotlists';
export function PlatformPicker({
  platforms,
  value,
  onChange,
}: {
  platforms: HotPlatform[];
  value: string[];
  onChange: (ids: string[]) => void;
}) {
  const option = (platform: HotPlatform) => ({
    value: platform.id,
    label: platform.name,
    searchText: `${platform.region} ${platform.category}`,
  });
  return (
    <GroupedFilterPicker
      title="选择热搜平台"
      placeholder="选择热搜平台（可多选）"
      summaryLabel="热搜平台"
      allLabel="全部热搜平台"
      searchPlaceholder="搜索平台，如：百度、小红书、YouTube"
      noun="平台"
      value={value}
      onChange={onChange}
      groups={[
        ...['国内', '国外'].map((region) => ({
          key: region,
          name: `${region}平台`,
          options: platforms.filter((platform) => platform.region === region).map(option),
        })),
        ...[...new Set(platforms.map((platform) => platform.category))].map((category) => ({
          key: `category:${category}`,
          name: category,
          options: platforms.filter((platform) => platform.category === category).map(option),
        })),
      ]}
    />
  );
}
