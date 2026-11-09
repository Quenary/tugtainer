import { TagSeverity } from '@shared/types/tag-severity.type';

/**
 * Update lifecycle hooks for a container
 */
export interface IContainerHooks {
  pre_update: string[];
  post_update: string[];
  pre_stop: string[];
  pre_rollback: string[];
  post_rollback: string[];
}
/**
 * Container data
 */
export interface IContainerListItem {
  host_id: number;
  id: number;
  name: string;
  image: string;
  container_id: string;
  ports: Record<string, IContainerPort[]>;
  status: EContainerStatus;
  health: string;
  protected: boolean;
  auto_check_label?: boolean | null;
  auto_update_label?: boolean | null;
  check_enabled: boolean;
  update_enabled: boolean;
  update_available: boolean;
  checked_at: string;
  updated_at: string;
  remote_digests_changed_at: string | null;
  delay_update_for: number | null;
  healthcheck_timeout: number | null;
  /**
   * Image the container ran before the last successful update.
   * Digests pin the exact image, tags and version are informational.
   */
  previous_image_digests: string[] | null;
  previous_image_tags: string[] | null;
  previous_image_version: string | null;
  current_version: string | null;
  /** Version label of a pending digest update, when the registry config has one. */
  available_version: string | null;
  /** Build time of a pending digest update. */
  available_created: string | null;
  created_at: string;
  modified_at: string;
  exit_code: number;
  hooks: IContainerHooks | null;
}
export interface IContainerPort {
  HostIp: string;
  HostPort: string;
}
/**
 * Container inspect result
 */
export interface IContainerInspectResult {
  id?: string | null;
  created?: string | null;
  path?: string | null;
  args?: string[] | null;
  state?: Record<string, unknown> | null;
  image?: string | null;
  resolv_conf_path?: string | null;
  hostname_path?: string | null;
  hosts_path?: string | null;
  log_path?: string | null;
  name?: string | null;
  restart_count?: number | null;
  driver?: string | null;
  platform?: string | null;
  mount_label?: string | null;
  process_label?: string | null;
  app_armor_profile?: string | null;
  exec_ids?: string[] | null;
  host_config?: Record<string, unknown> | null;
  graph_driver?: Record<string, unknown> | null;
  size_rw?: number | null;
  size_root_fs?: number | null;
  mounts?: Record<string, unknown>[] | null;
  config?: Record<string, unknown> | null;
  network_settings?: Record<string, unknown> | null;
  pod?: string | null;
}
/**
 * Container full info
 */
export interface IContainerInfo {
  item: IContainerListItem | null;
  inspect: IContainerInspectResult;
}
/**
 * Container patch request body
 */
export interface IContainerPatchBody {
  check_enabled?: boolean;
  update_enabled?: boolean;
  delay_update_for?: number | null;
  healthcheck_timeout?: number | null;
  hooks?: IContainerHooks;
}
/**
 * Possible docker container statuses
 */
export enum EContainerStatus {
  created = 'created',
  restarting = 'restarting',
  running = 'running',
  removing = 'removing',
  paused = 'paused',
  exited = 'exited',
  dead = 'dead',
}
/**
 * Mapping of container status to tag severity color
 */
export const EContainerStatusSeverity: Record<EContainerStatus, TagSeverity> = {
  [EContainerStatus.created]: 'contrast',
  [EContainerStatus.paused]: 'secondary',
  [EContainerStatus.running]: 'success',
  [EContainerStatus.restarting]: 'info',
  [EContainerStatus.removing]: 'warn',
  [EContainerStatus.exited]: 'danger',
  [EContainerStatus.dead]: 'danger',
};
/**
 * Mapping of container health status to tag severity color
 */
export const EContainerHealthSeverity: Record<string, TagSeverity> = {
  healthy: 'success',
  unhealthy: 'danger',
};

export type TControlContainerCommand =
  'start' | 'stop' | 'restart' | 'kill' | 'pause' | 'unpause';

export interface IGetContainerLogsRequestBody {
  details?: boolean;
  since?: Date;
  tail?: number;
  timestamps: boolean;
  until: Date;
}
