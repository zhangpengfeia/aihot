import {
ArrowUpOutlined,
BookOutlined,
StarOutlined
} from "@ant-design/icons";
import type { TableProps } from "antd";
import {
Button,
Grid,
Space,
Table,
Tag,
Typography
} from "antd";
import type { ReactNode } from 'react';
import { type Snapshot } from '../../../types/skills';
const {Text,Paragraph}=Typography;
export function RankingTable({items,loading,empty,onSelect}:{items:Snapshot[];loading:boolean;empty:ReactNode;onSelect:(id:number)=>void}){
const screens=Grid.useBreakpoint();
  const columns: TableProps<Snapshot>['columns'] = [
    {
      title: '排名',
      dataIndex: 'rank',
      width: 76,
      render: (rank: number) => (
        <span className={`rank-badge ${rank <= 3 ? `rank-${rank}` : ''}`}>{rank}</span>
      ),
    },
    {
      title: '项目',
      key: 'project',
      width: 480,
      render: (_, item) => (
        <div className="project-cell">
          <Button type="link" className="project-link" onClick={() => onSelect(item.id)}>
            {item.full_name}
          </Button>
          <Paragraph
            className="project-description"
            ellipsis={{ rows: 2, tooltip: item.description }}
          >
            {item.description || '暂无简介，查看 README 了解详情。'}
          </Paragraph>
          <Space size={[5, 5]} wrap>
            <Tag variant="filled">{item.language || '未标注语言'}</Tag>
            <Tag variant="filled">{item.license || '未声明许可证'}</Tag>
            <Tag color="blue" variant="filled">
              Skills 规则匹配
            </Tag>
            {item.categories?.map((category) => (
              <Tag color="geekblue" key={category}>
                {category}
              </Tag>
            ))}
          </Space>
        </div>
      ),
    },
    {
      title: (
        <Space size={5}>
          <StarOutlined />
          累计 Star
        </Space>
      ),
      dataIndex: 'stars',
      width: 140,
      align: 'right',
      render: (value: number) => (
        <Text strong className="numeric">
          {value.toLocaleString()}
        </Text>
      ),
    },
    {
      title: '24h 净增长',
      dataIndex: 'delta_24h',
      width: 145,
      align: 'right',
      render: (value: number | null) =>
        value === null ? (
          <Text type="secondary">数据积累中</Text>
        ) : (
          <Text
            className="numeric"
            type={value > 0 ? 'success' : value < 0 ? 'danger' : 'secondary'}
          >
            {value > 0 && <ArrowUpOutlined />} {value.toLocaleString()}
          </Text>
        ),
    },
    {
      title: '操作',
      key: 'actions',
      width: 120,
      align: 'center',
      fixed: screens.md ? 'right' : undefined,
      render: (_, item) => (
        <Button icon={<BookOutlined />} onClick={() => onSelect(item.id)}>
          资料
        </Button>
      ),
    },
  ];

return (<Table<Snapshot>
                        columns={columns}
                        dataSource={items}
                        rowKey="id"
                        loading={loading}
                        pagination={false}
                        scroll={{ x: 960 }}
                        locale={{ emptyText: empty }}
                      />);}
