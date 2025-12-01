import { TIncomplete } from '../incomplete.type';

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
  ImagesDeleted: { [K: string]: string }[];
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
  ContainerConfig: TIncomplete;
  DockerVersion: string;
  Author: string;
  Config: TIncomplete;
  Architecture: string;
  Os: string;
  OsVersion: string;
  Variant: string;
  Size: number;
  VirtualSize: number;
  GraphDriver: TIncomplete;
  RootFS: TIncomplete;
  Metadata: TIncomplete;
}
