import { ContainersApiService } from 'src/app/features/containers/containers-api.service';
import { Mocked, vi } from 'vitest';

export const getContainersApiServiceMock = (): Mocked<ContainersApiService> => {
  const mock: Partial<Mocked<ContainersApiService>> = {
    list: vi.fn(),
    get: vi.fn(),
    checkContainer: vi.fn(),
    updateContainer: vi.fn(),
    hostState: vi.fn(),
    watchJobState: vi.fn() as Mocked<ContainersApiService>['watchJobState'],
    patch: vi.fn(),
    controlContainer: vi.fn(),
    checkAll: vi.fn(),
    updateAll: vi.fn(),
    checkHost: vi.fn(),
    updateHost: vi.fn(),
    hooksEnabled: vi.fn(),
  };
  return mock as Mocked<ContainersApiService>;
};
