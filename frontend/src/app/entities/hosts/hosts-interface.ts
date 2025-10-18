export type THostClientType = 'docker' | 'podman' | 'nerdctl' | 'unknown';
export interface ICreateHost {
  name: string;
  enabled: boolean;
  prune: boolean;
  config: string;
  context: string;
  host: string;
  tls: boolean;
  tlscacert: string;
  tlscert: string;
  tlskey: string;
  tlsverify: boolean;
  client_binary: string;
  client_call: string[];
  client_type: THostClientType;
}
export interface IHostInfo extends ICreateHost {
  id: number;
}
export interface IHostStatus {
  id: number;
  ok: boolean;
  err: string;
}
