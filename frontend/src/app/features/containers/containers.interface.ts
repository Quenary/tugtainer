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
  check_enabled: boolean;
  update_enabled: boolean;
  update_available: boolean;
  checked_at: string;
  updated_at: string;
  remote_digests_changed_at: string | null;
  delay_update_for: number | null;
  /**
   * Image the container ran before the last successful update.
   * Digests pin the exact image, tags and version are informational.
   */
  previous_image_digests: string[] | null;
  previous_image_tags: string[] | null;
  previous_image_version: string | null;
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
  Id: string;
  Created: string;
  Path: string;
  Args: string[];
  State: Record<string, unknown>;
  Image: string;
  Pod: string;
  ResolvConfPath: string;
  HostnamePath: string;
  HostsPath: string;
  LogPath: string;
  Node: string;
  Name: string;
  RestartCount: number;
  Driver: string;
  Platform: string;
  MountLabel: string;
  ProcessLabel: string;
  AppArmorProfile: string;
  ExecIDs: string[];
  HostConfig: Record<string, unknown>;
  GraphDriver: Record<string, unknown>;
  SizeRw: number;
  SizeRootFs: number;
  Mounts: Record<string, unknown>[];
  Config: Record<string, unknown>;
  NetworkSettings: Record<string, unknown>;
  Namespace: string;
  IsInfra: boolean;
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
 * Mapping of container status to primeng severity color
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
 * Mapping of container health status to primeng severity color
 */
export const EContainerHealthSeverity: Record<string, TagSeverity> = {
  healthy: 'success',
  unhealthy: 'danger',
};

export type TControlContainerCommand =
  | 'start'
  | 'stop'
  | 'restart'
  | 'kill'
  | 'pause'
  | 'unpause';

export interface IGetContainerLogsRequestBody {
  details?: boolean;
  since?: Date;
  tail?: number;
  timestamps: boolean;
  until: Date;
}
