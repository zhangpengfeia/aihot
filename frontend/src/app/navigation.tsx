import { BookOutlined, BulbOutlined, FireOutlined, StarOutlined } from '@ant-design/icons';
import type { MenuProps } from 'antd';
export type ViewKey =
  | 'hotlists'
  | 'users'
  | 'library'
  | 'today'
  | 'history'
  | 'knowledge'
  | 'sources'
  | 'categories'
  | 'favorites'
  | 'summary'
  | 'status'
  | 'creation';
export const navigationItems: MenuProps['items'] = [
  { key: 'summary', icon: <FireOutlined />, label: '首页看板' },
  {
    key: 'skills',
    icon: <BookOutlined />,
    label: 'Skill 库',
    children: [
      { key: 'library', label: '项目资料' },
      { key: 'today', label: '今日热榜' },
      { key: 'history', label: '历史热榜' },
    ],
  },
  {
    key: 'knowledge-group',
    icon: <BulbOutlined />,
    label: '知识库',
    children: [
      { key: 'knowledge', label: '知识选题库' },
      { key: 'hotlists', label: '全网热搜' },
      { key: 'sources', label: '采集接口管理' },
    ],
  },
  {
    key: 'creator-center',
    icon: <BulbOutlined />,
    label: '创作者中心',
    children: [
      { key: 'favorites', icon: <StarOutlined />, label: '收藏与个人备注' },
      { key: 'creation', label: '选题创作看板' },
    ],
  },
];
export const viewLabels: Record<ViewKey, string> = {
  hotlists: '知识库 / 全网热搜',
  users: '用户管理',
  library: 'Skill 库 / 项目资料',
  today: 'Skill 库 / 今日热榜',
  history: 'Skill 库 / 历史热榜',
  knowledge: '知识选 / 知识选题库',
  sources: '知识选 / 采集接口管理',
  categories: '分类整理',
  favorites: '收藏与个人备注',
  summary: '首页看板',
  status: '采集状态面板',
  creation: '创作者中心 / 选题创作看板',
};
