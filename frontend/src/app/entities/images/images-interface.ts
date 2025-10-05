export interface IImage {
  repository: string;
  id: string;
  dangling: boolean;
  unused: boolean;
  tags: string[];
  size: number;
}

export interface IImagePruneResult {
  ImagesDeleted: { [K: string]: string }[];
  SpaceReclaimed: number;
}
