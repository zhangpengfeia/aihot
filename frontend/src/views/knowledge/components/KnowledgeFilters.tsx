import { Card, DatePicker, Flex, Input, Select } from 'antd';
import type { useKnowledgeTopics } from '../hooks/useKnowledgeTopics';
export function KnowledgeFilters(state: ReturnType<typeof useKnowledgeTopics>) {
  const {
    labels,
    setLabels,
    region,
    setRegion,
    setPage,
    setQ,
    meta,
    kind,
    setKind,
    sourceId,
    setSourceId,
    sortBy,
    setSortBy,
    setDay,
  } = state;
  const seen = new Set(meta.categories);
  const groups = Object.entries(meta.tag_groups ?? {})
    .map(([group, tags]) => ({
      label: group,
      options: tags
        .filter((value) => {
          if (seen.has(value)) return false;
          seen.add(value);
          return true;
        })
        .map((value) => ({ label: value, value })),
    }))
    .filter((group) => group.options.length > 0);
  return (
    <Card size="small">
      <Flex gap={12} wrap>
        <Select
          aria-label="内容分类与标签"
          mode="multiple"
          placeholder="内容分类 / 热门与小众标签（可多选）"
          showSearch
          allowClear
          maxTagCount="responsive"
          optionFilterProp="label"
          value={labels}
          onChange={(values) => {
            setLabels(values);
            setPage(1);
          }}
          style={{ width: 360, maxWidth: '100%' }}
          options={[
            {
              label: '已有内容分类',
              options: meta.categories.map((value) => ({ label: value, value })),
            },
            ...groups,
          ]}
        />
        <Select
          aria-label="题材地区"
          placeholder="国内 / 国外"
          allowClear
          value={region}
          onChange={(value) => {
            setRegion(value);
            setPage(1);
          }}
          style={{ width: 150 }}
          options={[
            { label: '国内题材', value: '国内' },
            { label: '国外题材', value: '国外' },
          ]}
        />
        <Input.Search
          aria-label="搜索知识选题"
          placeholder="搜索标题或摘要"
          allowClear
          onSearch={(value) => {
            setQ(value);
            setPage(1);
          }}
          style={{ width: 280 }}
        />
        <Select
          aria-label="选题类型"
          placeholder="全部选题类型"
          allowClear
          value={kind}
          onChange={(value) => {
            setKind(value);
            setPage(1);
          }}
          style={{ width: 170 }}
          options={['热点候选', '知识探索'].map((value) => ({ label: value, value }))}
        />
        <Select
          aria-label="采集接口"
          placeholder="全部采集接口"
          allowClear
          showSearch
          optionFilterProp="label"
          value={sourceId}
          onChange={(value) => {
            setSourceId(value);
            setPage(1);
          }}
          style={{ width: 220 }}
          options={meta.sources.filter((s) => s.id).map((s) => ({ value: s.id!, label: s.name }))}
        />
        <Select
          aria-label="排序方式"
          value={sortBy}
          onChange={(value) => {
            setSortBy(value);
            setPage(1);
          }}
          style={{ width: 160 }}
          options={[
            { value: 'published', label: '按发布日期排序' },
            { value: 'collected', label: '按入库时间排序' },
          ]}
        />
        <DatePicker
          aria-label="发布日期"
          placeholder="发布日期"
          onChange={(value) => {
            setDay(value?.format('YYYY-MM-DD') ?? '');
            setPage(1);
          }}
        />
      </Flex>
    </Card>
  );
}
