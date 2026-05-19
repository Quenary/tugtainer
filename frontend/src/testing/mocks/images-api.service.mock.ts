import { ImagesApiService } from 'src/app/features/images/images-api.service';
import { Mocked, vi } from 'vitest';

export const getImagesApiServiceMock = (): Mocked<ImagesApiService> => {
  const mock: Partial<ImagesApiService> = {
    list: vi.fn(),
    inspect: vi.fn(),
    prune: vi.fn(),
  };
  return mock as Mocked<ImagesApiService>;
};
