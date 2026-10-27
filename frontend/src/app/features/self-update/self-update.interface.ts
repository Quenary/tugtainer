export type TSelfUpdateStatus =
  | 'pending'
  | 'running'
  | 'succeeded'
  | 'aborted'
  | 'rolled_back'
  | 'failed'
  | 'interrupted';

export const FINAL_SELF_UPDATE_STATUSES: readonly TSelfUpdateStatus[] = [
  'succeeded',
  'aborted',
  'rolled_back',
  'failed',
  'interrupted',
];

export interface ISelfUpdateState {
  status: TSelfUpdateStatus;
  container_name: string;
  old_container_id: string;
  new_container_id: string | null;
  helper_container_name: string;
  old_image_id: string;
  new_image_id: string;
  old_version: string | null;
  new_version: string | null;
  error: string | null;
  warnings: string[];
  started_at: string;
  finished_at: string | null;
}

export interface ISelfUpdateStatusResponse {
  allowed: boolean;
  state: ISelfUpdateState | null;
}
