import {
  Alert,
  Button,
  Card,
  Flex,
  Input,
  Modal,
  Popconfirm,
  Select,
  Space,
  Spin,
  Tag,
  Typography,
  message,
} from 'antd';
import { useState } from 'react';
import { write } from '../../api/http';
import { PageHeading as Heading } from '../../components/common/PageHeading';
import { useResource } from '../../hooks/useResource';
import { CREATION_STAGES, type CreationCard } from '../../types/workspace';
const { Text, Paragraph } = Typography;
export function CreationBoardPage({ tick }: { tick: number }) {
  const [q, setQ] = useState('');
  const resource = useResource<{ items: CreationCard[] }>(
    `/workspace/cards?q=${encodeURIComponent(q)}`,
    tick,
  );
  const [selected, setSelected] = useState<CreationCard | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [notice, context] = message.useMessage();
  async function update(card: CreationCard, fields: Partial<CreationCard>) {
    await write(`/workspace/cards/${card.id}`, 'PATCH', fields);
    resource.refresh();
  }
  return (
    <>
      {context}
      <Heading
        title="选题创作看板"
        description="从知识选题加入卡片，按创作进度整理脚本和成品链接。"
        {...resource}
      />
      <Space orientation="vertical" size={16} className="full-width">
        <Input.Search
          aria-label="搜索创作卡片"
          placeholder="搜索选题标题"
          allowClear
          onSearch={setQ}
          style={{ maxWidth: 360 }}
        />
        {resource.error && <Alert type="error" showIcon title={resource.error} />}
        {!resource.loading && resource.data?.items.length === 0 && (
          <Alert type="info" showIcon title="暂无创作卡片，请在知识选题库点击“加入创作看板”。" />
        )}
        <Spin spinning={resource.loading}>
          <div className="creation-board">
            {CREATION_STAGES.map((stage, index) => {
              const items = (resource.data?.items ?? []).filter((card) => card.stage === stage);
              return (
                <section key={stage} className={`creation-column creation-column-${index}`}>
                  <Flex justify="space-between" className="creation-column-heading">
                    <Text strong>{stage}</Text>
                    <Tag>{items.length}</Tag>
                  </Flex>
                  <Space orientation="vertical" size={12} className="full-width">
                    {items.map((card) => (
                      <Card key={card.id} size="small">
                        <Space orientation="vertical" className="full-width" size={12}>
                          <Text strong>{card.title}</Text>
                          <Tag>{card.category}</Tag>
                          <Paragraph
                            type="secondary"
                            ellipsis={{ rows: 3 }}
                            style={{ whiteSpace: 'pre-wrap', margin: 0 }}
                          >
                            {card.script || '还没有脚本，点击编辑开始整理。'}
                          </Paragraph>
                          {card.output_url && (
                            <a href={card.output_url} target="_blank" rel="noreferrer">
                              查看成品
                            </a>
                          )}
                          <Select
                            aria-label={`调整阶段：${card.title}`}
                            value={card.stage}
                            className="full-width"
                            options={CREATION_STAGES.map((value) => ({ value, label: value }))}
                            onChange={async (value) => {
                              try {
                                await update(card, { stage: value });
                              } catch (e) {
                                notice.error((e as Error).message);
                              }
                            }}
                          />
                          <Flex justify="space-between">
                            <Button
                              onClick={() => {
                                setSelected({ ...card });
                                setError('');
                              }}
                            >
                              编辑脚本
                            </Button>
                            <Popconfirm
                              title="删除这张创作卡片？"
                              description="不会删除原始选题。"
                              onConfirm={async () => {
                                try {
                                  await write(`/workspace/cards/${card.id}`, 'DELETE');
                                  resource.refresh();
                                } catch (e) {
                                  notice.error((e as Error).message);
                                }
                              }}
                            >
                              <Button danger type="text">
                                删除
                              </Button>
                            </Popconfirm>
                          </Flex>
                        </Space>
                      </Card>
                    ))}
                    {!items.length && <Text type="secondary">暂无选题</Text>}
                  </Space>
                </section>
              );
            })}
          </div>
        </Spin>
      </Space>
      <Modal
        title="编辑创作卡片"
        open={selected !== null}
        width={800}
        onCancel={() => setSelected(null)}
        okText="保存"
        cancelText="取消"
        confirmLoading={busy}
        onOk={async () => {
          if (!selected) return;
          setBusy(true);
          setError('');
          try {
            await update(selected, {
              stage: selected.stage,
              script: selected.script,
              output_url: selected.output_url,
            });
            setSelected(null);
            notice.success('创作卡片已保存');
          } catch (e) {
            setError((e as Error).message);
          } finally {
            setBusy(false);
          }
        }}
      >
        {selected && (
          <Space orientation="vertical" className="full-width" size={16}>
            {error && <Alert type="error" showIcon title={error} />}
            <Text strong>{selected.title}</Text>
            <a href={selected.source_url} target="_blank" rel="noreferrer">
              阅读原始资料
            </a>
            <Select
              aria-label="创作阶段"
              value={selected.stage}
              options={CREATION_STAGES.map((value) => ({ value, label: value }))}
              onChange={(stage) => setSelected({ ...selected, stage })}
            />
            <label htmlFor="creation-script">脚本</label>
            <Input.TextArea
              id="creation-script"
              value={selected.script}
              rows={12}
              maxLength={100000}
              showCount
              placeholder="整理开场、素材、解说与结尾……"
              onChange={(e) => setSelected({ ...selected, script: e.target.value })}
            />
            <label htmlFor="creation-output">成品链接</label>
            <Input
              id="creation-output"
              value={selected.output_url}
              maxLength={2000}
              placeholder="https://..."
              onChange={(e) => setSelected({ ...selected, output_url: e.target.value })}
            />
          </Space>
        )}
      </Modal>
    </>
  );
}
