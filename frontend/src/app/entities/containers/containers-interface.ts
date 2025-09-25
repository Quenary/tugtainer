/**
 * Container data
 */
export interface IContainer {
  name: string;
  image: string;
  short_id: string;
  ports: {
    [K: string]: IContainerPort[];
  };
  status: EContainerStatus;
  health: string;
  is_self: boolean;
  check_enabled: boolean;
  update_enabled: boolean;
  update_available: boolean;
  checked_at: string;
  updated_at: string;
  created_at: string;
  modified_at: string;
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
  progress: number;
  available: number;
  updated: number;
  failed: number;
}
