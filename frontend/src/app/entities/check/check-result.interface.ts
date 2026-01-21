import { IContainerInspectResult } from '../containers/containers-interface';
import { IImageInspectResult } from '../images/images-interface';
import { TIncomplete } from '../incomplete.type';

/**
 * Result of container check
 */
export type TContainerCheckResult =
  | 'not_available'
  | 'available'
  | 'available(notified)'
  | 'updated'
  | 'rolled_back'
  | 'failed'
  | null;

export interface IContainerCheckResult {
  container: IContainerInspectResult;
  local_image: IImageInspectResult | null;
  remote_image: IImageInspectResult | null;
  local_digests: string[];
  remote_digests: string[];
  result: TContainerCheckResult;
}

export interface IGroupCheckResult {
  host_id: number;
  host_name: string;
  items: IContainerCheckResult[];
}

export interface IHostCheckResult extends IGroupCheckResult {
  prune_result: string | null;
}
