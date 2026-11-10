export interface IImage {
  repository: string;
  id: string;
  dangling: boolean;
  unused: boolean;
  tags: string[];
  size: number;
  created: string;
}

export interface IPruneImageRequestBodySchema {
  all: boolean;
}

export interface IImageInspectResult {
  id?: string | null;
  repo_tags?: string[] | null;
  repo_digests?: string[] | null;
  parent?: string | null;
  comment?: string | null;
  created?: string | null;
  container?: string | null;
  container_config?: Record<string, unknown> | null;
  docker_version?: string | null;
  author?: string | null;
  config?: Record<string, unknown> | null;
  architecture?: string | null;
  os?: string | null;
  variant?: string | null;
  size?: number | null;
  virtual_size?: number | null;
  graph_driver?: Record<string, unknown> | null;
  root_fs?: Record<string, unknown> | null;
  metadata?: Record<string, unknown> | null;
}
