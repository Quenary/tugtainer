/**
 * Container data
 */
export interface IContainer {
  name: string;
  short_id: string;
  ports: {
    [K: string]: IContainerPort[];
  };
  status: EContainerStatus;
  health: string;
  is_self: boolean;
  check_enabled: boolean;
  update_enabled: boolean;
}
export interface IContainerPort {
  HostIp: string;
  HostPort: string;
}

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

export enum ECheckStatus {
  COLLECTING = 'COLLECTING',
  CHECKING = 'CHECKING',
  UPDATING = 'UPDATING',
  DONE = 'DONE',
}
export interface ICheckProgress {
  status: ECheckStatus;
  total_for_check: number;
  updatable: number;
  not_updated: number;
  updated: number;
  failed: number;
  progress: number;
}
