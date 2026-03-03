import {
  IContainerActionResult,
  IGroupActionResult,
  IHostActionResult,
} from './check-result.interface';

/**
 * Possible check/update progress statuses
 */
export enum EActionStatus {
  PREPARING = 'PREPARING',
  CHECKING = 'CHECKING',
  UPDATING = 'UPDATING',
  DONE = 'DONE',
  ERROR = 'ERROR',
}

export interface IActionProgress {
  status: EActionStatus;
}
export interface IContainerActionProgress extends IActionProgress {
  result?: IContainerActionResult;
}
/**
 * Group update progress cache
 */
export interface IGroupActionProgress extends IActionProgress {
  result?: IGroupActionResult;
}
/**
 * Host check/update progress cache
 */
export interface IHostActionProgress extends IActionProgress {
  result?: IHostActionResult;
}
/**
 * all hosts check/update progress cache
 */
export interface IAllActionProgress extends IActionProgress {
  result?: Record<string, IHostActionResult>;
}
