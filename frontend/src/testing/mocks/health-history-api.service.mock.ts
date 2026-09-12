import { HealthHistoryApiService } from 'src/app/features/health-history/health-history-api.service';
import { Mocked, vi } from 'vitest';

export const getHealthHistoryApiServiceMock =
  (): Mocked<HealthHistoryApiService> => {
    const mock: Partial<HealthHistoryApiService> = {
      getHistory: vi.fn(),
    };
    return mock as Mocked<HealthHistoryApiService>;
  };
