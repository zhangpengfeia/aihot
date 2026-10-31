export interface HotSource {
  id: number;
  name: string;
  enabled: boolean;
  status: string;
  error: string | null;
  observed_at: string | null;
  category?: string;
  region?: '国内' | '国外';
  items: {
    id: number;
    title: string;
    source_url: string;
    score: number | null;
    score_label?: string | null;
    rank: number;
  }[];
}
export interface HotPlatform extends Omit<HotSource, 'id'> {
  id: string;
  region: '国内' | '国外';
  category: string;
  connection_status: 'reserved' | 'configured';
  source_count: number;
  source_name?: string | null;
}
