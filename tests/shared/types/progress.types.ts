/**
 * Possible check/update progress statuses from the containers progress API.
 * Mirrors backend EActionStatus / frontend EActionStatus.
 */
export type ActionStatus =
  'PREPARING' | 'CHECKING' | 'UPDATING' | 'DONE' | 'ERROR';

export interface ActionProgress {
  status: ActionStatus;
}
