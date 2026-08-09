/**
 * Result of a container check/update action.
 * Mirrors backend ContainerCheckResultType / frontend TContainerCheckResult.
 */
export type ContainerCheckResult =
  | 'not_available'
  | 'available'
  | 'available(notified)'
  | 'updated'
  | 'rolled_back'
  | 'failed'
  | null;

export interface ContainerActionResult {
  result: ContainerCheckResult;
  image_spec: string | null;
}
