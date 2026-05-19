/* eslint-disable @typescript-eslint/no-empty-function */
import { TestBed } from '@angular/core/testing';
import { PendingTasks } from '@angular/core';
import { of, throwError } from 'rxjs';
import { Mocked } from 'vitest';
import { AppStore } from './app.store';
import { AuthApiService } from './features/auth/auth-api.service';
import { PublicApiService } from './features/public/public-api.service';
import { ToastService } from './core/services/toast.service';
import {
  IsUpdateAvailableResponseBody,
  IVersion,
} from './features/public/public-interface';
import { getToastServiceMock } from '@testing/mocks/toast-service.mock';
import { getPublicApiServiceMock } from '@testing/mocks/public-api.service.mock';
import { getAuthApiServiceMock } from '@testing/mocks/auth-api.service.mock';

describe('AppStore', () => {
  let store: InstanceType<typeof AppStore>;

  let authApiServiceMock: Mocked<AuthApiService>;
  let publicApiServiceMock: Mocked<PublicApiService>;
  let toastServiceMock: Mocked<ToastService>;

  beforeEach(() => {
    authApiServiceMock = getAuthApiServiceMock();
    authApiServiceMock.isDisabled.mockReturnValue(of(false));

    publicApiServiceMock = getPublicApiServiceMock();
    publicApiServiceMock.getVersion.mockReturnValue(of({} as IVersion));
    publicApiServiceMock.isUpdateAvailable.mockReturnValue(
      of({} as IsUpdateAvailableResponseBody),
    );

    toastServiceMock = getToastServiceMock();

    TestBed.configureTestingModule({
      providers: [
        AppStore,
        PendingTasks,
        {
          provide: AuthApiService,
          useValue: authApiServiceMock,
        },
        {
          provide: PublicApiService,
          useValue: publicApiServiceMock,
        },
        {
          provide: ToastService,
          useValue: toastServiceMock,
        },
      ],
    });

    store = TestBed.inject(AppStore);
  });

  it('should create store', () => {
    expect(store).toBeTruthy();
  });

  describe('loadIsAuthDisabled', () => {
    it('should load', () => {
      authApiServiceMock.isDisabled.mockReturnValue(of(true));

      store.loadIsAuthDisabled();

      expect(store.isAuthDisabled()).toBe(true);
    });

    it('should show error', () => {
      const error = new Error('Test');
      authApiServiceMock.isDisabled.mockReturnValue(throwError(() => error));

      store.loadIsAuthDisabled();

      expect(toastServiceMock.error).toHaveBeenCalledWith(error);
    });
  });

  describe('loadVersion', () => {
    it('should load', () => {
      const version: IVersion = {
        image_version: '1.0.0',
      };
      publicApiServiceMock.getVersion.mockReturnValue(of(version));

      store.loadVersion();

      expect(store.version()).toEqual(version);
    });

    it('should show error', () => {
      const error = new Error('Test');
      publicApiServiceMock.getVersion.mockReturnValue(throwError(() => error));
      const consoleErrorSpy = vi
        .spyOn(console, 'error')
        .mockImplementation(() => {});

      store.loadVersion();

      expect(consoleErrorSpy).toHaveBeenCalledWith(error);
    });
  });

  describe('loadUpdate', () => {
    it('should load', () => {
      const update: IsUpdateAvailableResponseBody = {
        is_available: true,
        release_url: 'test',
      };
      publicApiServiceMock.isUpdateAvailable.mockReturnValue(of(update));

      store.loadUpdate();

      expect(store.update()).toEqual(update);
    });

    it('should show error', () => {
      const error = new Error('Test');
      publicApiServiceMock.isUpdateAvailable.mockReturnValue(
        throwError(() => error),
      );
      const consoleErrorSpy = vi
        .spyOn(console, 'error')
        .mockImplementation(() => {});

      store.loadUpdate();

      expect(consoleErrorSpy).toHaveBeenCalledWith(error);
    });
  });

  describe('setTheme', () => {
    it('should set theme', () => {
      store.setTheme('DARK');

      expect(store.theme()).toBe('DARK');
      expect(document.documentElement.className).toBe('DARK');
    });

    it('should resolve AUTO to DARK', () => {
      vi.stubGlobal(
        'matchMedia',
        vi.fn().mockReturnValue({ matches: true } as MediaQueryList),
      );

      store.setTheme('AUTO');

      expect(document.documentElement.className).toBe('DARK');
    });

    it('should resolve AUTO to LIGHT', () => {
      vi.stubGlobal(
        'matchMedia',
        vi.fn().mockReturnValue({ matches: false } as MediaQueryList),
      );

      store.setTheme('AUTO');

      expect(document.documentElement.className).toBe('LIGHT');
    });
  });
});
