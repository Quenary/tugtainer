import type { ContainerActionResult } from './check-result.types';
import type { ActionProgress } from './progress.types';

/** Subset of GET /api/containers/{host_id}/list item used by tests. */
export interface ContainerListItem {
  name: string;
  update_available: boolean | null;
}

export interface ContainerActionProgress extends ActionProgress {
  result?: ContainerActionResult;
}
