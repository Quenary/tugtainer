/**
 * Container data
 */
export interface IContainer {
  id: number;
  name: string;
  image: string;
  container_id: string;
  ports: {
    [K: string]: IContainerPort[];
  };
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
}
export interface IContainerPort {
  host_ip: string;
  host_port: string;
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
  PREPARING = 'PREPARING',
  CHECKING = 'CHECKING',
  UPDATING = 'UPDATING',
  DONE = 'DONE',
  ERROR = 'ERROR',
}

export interface IContainerCheckData {
  status: ECheckStatus;
}
export interface IHostCheckData extends IContainerCheckData {
  available: number;
  updated: number;
  rolled_back: number;
  failed: number;
}
export interface IAllCheckData extends IHostCheckData {}
