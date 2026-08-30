/** Subset of GET /api/containers/{host_id}/list item used by tests. */
export interface ContainerListItem {
  name: string;
  update_available: boolean | null;
}
