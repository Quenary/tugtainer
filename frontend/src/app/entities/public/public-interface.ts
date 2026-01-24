export interface IVersion {
  image_version: string;
}

export interface IsUpdateAvailableResponseBody {
  is_available: boolean;
  release_url: string;
}
