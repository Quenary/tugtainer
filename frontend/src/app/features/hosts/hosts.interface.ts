export interface IHostBase {
  name: string;
  enabled: boolean;
  prune: boolean;
  prune_all: boolean;
  url: string;
  ssl: boolean;
  timeout: number;
  container_hc_timeout: number;
}

export interface IHostCreate extends IHostBase {
  secret: string | null;
}

export interface IHostUpdate extends IHostBase {
  is_changing_secret: boolean;
  secret: string | null;
}

export interface IHostInfo extends IHostBase {
  id: number;
  has_secret: boolean;
  available_updates_count: number;
}

export interface IHostStatus {
  id: number;
  ok: boolean;
  err: string;
}
