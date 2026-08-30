import { TagSeverity } from '@shared/types/tag-severity.type';
import { IContainerInspectResult } from '../../features/containers/containers.interface';
import { IImageInspectResult } from '../../features/images/images.interface';

export type TContainerJobOutcome =
  | 'not_available'
  | 'available'
  | 'available(notified)'
  | 'updated'
  | 'rolled_back'
  | 'failed'
  | null;

export interface IContainerJobResult {
  container: IContainerInspectResult;
  result: TContainerJobOutcome;
  image_spec: string | null;
  local_image: IImageInspectResult | null;
  remote_image: IImageInspectResult | null;
  local_digests: string[];
  remote_digests: string[];
}

export const ContainerJobOutcomeSeverity: Record<
  TContainerJobOutcome,
  TagSeverity
> = {
  'available': 'success',
  'available(notified)': 'success',
  'updated': 'info',
  'not_available': 'contrast',
  'rolled_back': 'warn',
  'failed': 'danger',
};
