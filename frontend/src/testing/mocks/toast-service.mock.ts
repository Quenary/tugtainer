import { ToastService } from 'src/app/core/services/toast.service';
import { Mocked, vi } from 'vitest';

export const getToastServiceMock = (): Mocked<ToastService> => {
  const mock: Partial<Mocked<ToastService>> = {
    error: vi.fn(),
    success: vi.fn(),
  };
  return mock as Mocked<ToastService>;
};
