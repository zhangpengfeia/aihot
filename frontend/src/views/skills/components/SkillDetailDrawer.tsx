import {
BookOutlined,
DownloadOutlined,
GithubOutlined
} from "@ant-design/icons";
import {
Alert,
Button,
Descriptions,
Drawer,
Grid,
Space,
Spin,
Typography
} from "antd";
import { useEffect,useState } from "react";
import { get } from '../../../api/http';
import { PersonalButton } from "../../../components/workspace/PersonalActions";
import { type Snapshot } from '../../../types/skills';
import { formatTime } from '../../../utils/date';
const {Title,Text,Paragraph}=Typography;
export function SkillDetailDrawer({selected,onClose}:{selected:number|null;onClose:()=>void}){
const screens=Grid.useBreakpoint();const [detail,setDetail]=useState<Snapshot|null>(null);const [detailError,setDetailError]=useState('');
  useEffect(() => {
    setDetail(null);
    setDetailError('');
    if (selected === null) return;
    const controller = new AbortController();
    get<Snapshot>(`/snapshots/${selected}`, controller.signal)
      .then(setDetail)
      .catch((e) => {
        if (!controller.signal.aborted) setDetailError((e as Error).message);
      });
    return () => controller.abort();
  }, [selected]);

return (<Drawer
        title={
          <Space>
            <BookOutlined />
            项目资料快照
          </Space>
        }
        open={selected !== null}
        onClose={onClose}
        size={screens.md ? 780 : '100%'}
      >
        {detailError ? (
          <Alert type="error" showIcon title={detailError} />
        ) : !detail ? (
          <div className="drawer-loading">
            <Spin tip="读取资料中…">
              <div style={{ height: 100 }} />
            </Spin>
          </div>
        ) : (
          <Space orientation="vertical" size={24} className="full-width">
            <div>
              <Title level={3} className="detail-title">
                {detail.full_name}
              </Title>
              <Paragraph type="secondary">{detail.description || '仓库暂无简介'}</Paragraph>
              <Space wrap>
                <PersonalButton kind="repository" targetId={detail.repo_id} />
                <Button type="primary" icon={<GithubOutlined />} href={detail.url} target="_blank">
                  原始仓库
                </Button>
                <Button icon={<DownloadOutlined />} href={`/api/snapshots/${detail.id}/markdown`}>
                  下载 Markdown
                </Button>
              </Space>
            </div>
            <Descriptions
              title="观测信息"
              column={1}
              size="small"
              bordered
              items={[
                { key: 'observed', label: '观测时间', children: formatTime(detail.observed_at) },
                { key: 'stars', label: '累计 Star', children: detail.stars.toLocaleString() },
                {
                  key: 'growth',
                  label: '24h 净增长',
                  children:
                    detail.delta_24h === null ? '数据积累中' : detail.delta_24h.toLocaleString(),
                },
                { key: 'baseline', label: '增长基线', children: formatTime(detail.baseline_at) },
                { key: 'evidence', label: '识别依据', children: detail.evidence },
                { key: 'pushed', label: '最近推送', children: formatTime(detail.pushed_at) },
                { key: 'forks', label: 'Fork 数', children: detail.forks.toLocaleString() },
                { key: 'license', label: '许可证', children: detail.license || '未声明' },
                {
                  key: 'categories',
                  label: '用途分类',
                  children: detail.categories?.join('、') || '其他',
                },
              ]}
            />
            <div>
              <Title level={5}>安装方式（原文摘录）</Title>
              <Text type="secondary">以下仅记录原项目说明，未经执行验证。</Text>
              <pre className="readme-content">{detail.installation || '请查看原始仓库文档。'}</pre>
            </div>
            <div>
              <Title level={5}>README 原始资料</Title>
              <Alert
                type="info"
                showIcon
                title="以下内容由项目作者提供，未经实测。保留采集时原文，最多 100,000 字符。"
              />
              <pre className="readme-content">{detail.readme || '该仓库暂无可读取的 README。'}</pre>
            </div>
          </Space>
        )}
      </Drawer>);}
