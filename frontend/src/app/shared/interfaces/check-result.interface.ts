import { IContainerInspectResult } from '../../features/containers/containers.interface';
import { IImageInspectResult } from '../../features/images/images.interface';

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

export interface IContainerActionResult {
  container: IContainerInspectResult;
  result: TContainerCheckResult;
  image_spec: string | null;
  local_image: IImageInspectResult | null;
  remote_image: IImageInspectResult | null;
  local_digests: string[];
  remote_digests: string[];
}

export interface IGroupActionResult {
  host_id: number;
  host_name: string;
  items: IContainerActionResult[];
}

export interface IHostActionResult extends IGroupActionResult {
  prune_result: string | null;
}
