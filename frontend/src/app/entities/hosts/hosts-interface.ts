export interface ICreateHost {
  name: string;
  enabled: boolean;
  prune: boolean;
  url: string;
  secret: string;
  timeout: number;
}
export interface IHostInfo extends ICreateHost {
  id: number;
}
export interface IHostStatus {
  id: number;
  ok: boolean;
  err: string;
}
