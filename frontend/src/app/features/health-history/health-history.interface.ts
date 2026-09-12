export interface IHealthHistoryFilterRequest {
  page?: number;
  limit?: number;
  host_id: number;
  container_id?: number;
  status?: string[];
}

export interface IHealthHistoryItem {
  id: number;
  host_id: number;
  container_id: number;
  container_name: string;
  status: string;
  restarted: boolean;
  notified: boolean;
  created_at: string;
}

export interface IHealthHistoryPagedResponse {
  total: number;
  page: number;
  limit: number;
  items: IHealthHistoryItem[];
}
