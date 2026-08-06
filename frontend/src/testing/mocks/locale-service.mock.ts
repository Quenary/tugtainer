import { LocaleService } from 'src/app/core/services/locale.service';
import { Mocked, vi } from 'vitest';

export const getLocaleServiceMock = (): Mocked<LocaleService> => {
  const mock: Partial<Mocked<LocaleService>> = {
    apply: vi.fn().mockResolvedValue(undefined),
  };
  return mock as Mocked<LocaleService>;
};
