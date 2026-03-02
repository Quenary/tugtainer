export interface ICreateHost {
  name: string;
  enabled: boolean;
  prune: boolean;
  prune_all: boolean;
  url: string;
  secret: string;
  ssl: boolean;
  timeout: number;
  container_hc_timeout: number;
}
export interface IHostInfo extends ICreateHost {
  id: number;
}
export interface IHostStatus {
  id: number;
  ok: boolean;
  err: string;
}
