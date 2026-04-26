export interface IImage {
  repository: string;
  id: string;
  dangling: boolean;
  unused: boolean;
  tags: string[];
  size: number;
}

export interface IPruneImageRequestBodySchema {
  all: boolean;
}

export interface IImagePruneResult {
  ImagesDeleted: Record<string, string>[];
  SpaceReclaimed: number;
}

export interface IImageInspectResult {
  Id: string;
  RepoTags: string[];
  RepoDigests: string[];
  Parent: string;
  Comment: string;
  Created: string;
  Container: string;
  ContainerConfig: Record<string, unknown>;
  DockerVersion: string;
  Author: string;
  Config: Record<string, unknown>;
  Architecture: string;
  Os: string;
  OsVersion: string;
  Variant: string;
  Size: number;
  VirtualSize: number;
  GraphDriver: Record<string, unknown>;
  RootFS: Record<string, unknown>;
  Metadata: Record<string, unknown>;
}
