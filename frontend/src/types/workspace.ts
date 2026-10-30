export interface PersonalItem {
  id?: number;
  target_kind: 'repository' | 'topic';
  target_id: number;
  favorite: boolean;
  note: string;
  title: string;
  url: string;
  snapshot_id?: number;
  topic_id?: number;
  updated_at?: string;
}

export const CREATION_STAGES = ['待筛选', '待创作', '制作中', '已发布'] as const;

export interface CreationCard {
  id: number;
  topic_id: number;
  title: string;
  category: string;
  source_url: string;
  stage: (typeof CREATION_STAGES)[number];
  script: string;
  output_url: string;
  updated_at: string;
}
