import { PublicApiService } from 'src/app/features/public/public-api.service';
import { Mocked, vi } from 'vitest';

export const getPublicApiServiceMock = (): Mocked<PublicApiService> => {
  const mock: Partial<PublicApiService> = {
    getVersion: vi.fn(),
    isUpdateAvailable: vi.fn(),
    getHealth: vi.fn(),
    getSummary: vi.fn(),
  };
  return mock as Mocked<PublicApiService>;
};
