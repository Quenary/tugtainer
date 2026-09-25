export interface IServiceListItem {
  id: string;
  name: string;
  image: string;
  mode: string;
  replicas_running: number;
  replicas_desired: number | null;
  check_enabled: boolean;
  update_enabled: boolean;
  update_available: boolean;
  checked_at: string | null;
  updated_at: string | null;
  update_status_state: string | null;
  update_status_message: string | null;
  labels: Record<string, string>;
}

export interface IServicePatchBody {
  check_enabled?: boolean;
  update_enabled?: boolean;
}

export interface IServiceTriggerRequestBody {
  names?: string[];
}
