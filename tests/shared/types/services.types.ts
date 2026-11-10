/** Subset of GET /api/hosts/{id}/services used by tests. */
export interface ServiceListItem {
  id: string;
  name: string;
  image: string;
  mode: string;
  replicas_running: number;
  replicas_desired: number | null;
  check_enabled: boolean;
  update_enabled: boolean;
  update_available: boolean;
  update_status_state: string | null;
}
