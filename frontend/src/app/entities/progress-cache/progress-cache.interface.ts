import { IGroupCheckResult, IHostCheckResult } from '../check/check-result.interface';

/**
 * Possible check progress statuses
 */
export enum ECheckStatus {
  PREPARING = 'PREPARING',
  CHECKING = 'CHECKING',
  UPDATING = 'UPDATING',
  DONE = 'DONE',
  ERROR = 'ERROR',
}

export interface IBaseCheckProgressCache {
  status: ECheckStatus;
}
/**
 * Group (container) check progress cache
 */
export interface IGroupCheckProgressCache extends IBaseCheckProgressCache {
  result?: IGroupCheckResult;
}
/**
 * Host check progress cache
 */
export interface IHostCheckProgressCache extends IBaseCheckProgressCache {
  result?: IHostCheckResult;
}
/**
 * All host's check progress cache
 */
export interface IAllCheckProgressCache extends IBaseCheckProgressCache {
  result?: Record<string, IHostCheckResult>;
}
