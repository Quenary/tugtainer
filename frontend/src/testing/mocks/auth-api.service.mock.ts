import { AuthApiService } from 'src/app/features/auth/auth-api.service';
import { Mocked, vi } from 'vitest';

export const getAuthApiServiceMock = (): Mocked<AuthApiService> => {
  const mock: Partial<AuthApiService> = {
    isDisabled: vi.fn(),
    isAuthProviderEnabled: vi.fn(),
    login: vi.fn(),
    initiateLogin: vi.fn(),
    refresh: vi.fn(),
    logout: vi.fn(),
    setPassword: vi.fn(),
    isAuthorized: vi.fn(),
    isPasswordSet: vi.fn(),
  };
  return mock as Mocked<AuthApiService>;
};
