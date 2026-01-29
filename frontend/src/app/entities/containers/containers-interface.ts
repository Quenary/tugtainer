import { TIncomplete } from '../incomplete.type';

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
  created_at: string;
  modified_at: string;
  exit_code: number;
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
  State: TIncomplete;
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
  HostConfig: TIncomplete;
  GraphDriver: TIncomplete;
  SizeRw: number;
  SizeRootFs: number;
  Mounts: TIncomplete[];
  Config: TIncomplete;
  NetworkSettings: TIncomplete;
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
export const EContainerStatusSeverity: Record<EContainerStatus, string> = {
  [EContainerStatus.created]: 'primary',
  [EContainerStatus.paused]: 'contrast',
  [EContainerStatus.running]: 'success',
  [EContainerStatus.restarting]: 'info',
  [EContainerStatus.removing]: 'warn',
  [EContainerStatus.exited]: 'danger',
  [EContainerStatus.dead]: 'danger',
};
/**
 * Mapping of container health status to primeng severity color
 */
export const EContainerHealthSeverity: Record<string, string> = {
  healthy: 'success',
  unhealthy: 'danger',
};

export type TControlContainerCommand = 'start' | 'stop' | 'restart' | 'kill' | 'pause' | 'unpause';

export interface IGetContainerLogsRequestBody {
  details?: boolean;
  since?: Date;
  tail?: number;
  timestamps: boolean;
  until: Date;
}
