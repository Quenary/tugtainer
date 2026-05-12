import { TestBed } from '@angular/core/testing';
import { of } from 'rxjs';
import { AppStore } from './app.store';
import { AuthApiService } from './features/auth/auth-api.service';
import { PublicApiService } from './features/public/public-api.service';
import { ToastService } from './core/services/toast.service';
import {
  IsUpdateAvailableResponseBody,
  IVersion,
} from './features/public/public-interface';
import { PendingTasks } from '@angular/core';
import { storageJson } from 'src/extensions/local-storage-json';
import { tick } from '@testing/test-utils';

describe('AppStore', () => {
  let store: InstanceType<typeof AppStore>;

  let authApiService: jasmine.SpyObj<AuthApiService>;
  let publicApiService: jasmine.SpyObj<PublicApiService>;
  let toastService: jasmine.SpyObj<ToastService>;

  beforeEach(() => {
    authApiService = jasmine.createSpyObj<AuthApiService>(
      'AuthApiService',
      [],
      {
        isDisabled: jasmine.createSpy('isDisabled').and.returnValue(of(false)),
      },
    );

    publicApiService = jasmine.createSpyObj<PublicApiService>(
      'PublicApiService',
      [],
      {
        getVersion: jasmine.createSpy('getVersion').and.returnValue(of({})),
        isUpdateAvailable: jasmine
          .createSpy('isUpdateAvailable')
          .and.returnValue(of({})),
      },
    );

    toastService = jasmine.createSpyObj<ToastService>('ToastService', [
      'error',
    ]);

    storageJson();

    TestBed.configureTestingModule({
      providers: [
        AppStore,
        PendingTasks,
        {
          provide: AuthApiService,
          useValue: authApiService,
        },
        {
          provide: PublicApiService,
          useValue: publicApiService,
        },
        {
          provide: ToastService,
          useValue: toastService,
        },
      ],
    });

    store = TestBed.inject(AppStore);
  });

  it('should create store', () => {
    expect(store).toBeTruthy();
  });

  it('should load auth disabled flag', async () => {
    authApiService.isDisabled.and.returnValue(of(true));
    store.loadIsAuthDisabled();
    await tick();
    expect(store.isAuthDisabled()).toBeTrue();
    expect(store.loading()).toBeFalse();
  });

  it('should load version', async () => {
    const version: IVersion = {
      image_version: '1.0.0',
    };
    publicApiService.getVersion.and.returnValue(of(version));
    store.loadVersion();
    await tick();
    expect(store.version()).toEqual(version);
    expect(store.loading()).toBeFalse();
  });

  it('should load update', async () => {
    const update: IsUpdateAvailableResponseBody = {
      is_available: true,
      release_url: 'test',
    };
    publicApiService.isUpdateAvailable.and.returnValue(of(update));
    store.loadUpdate();
    await tick();
    expect(store.update()).toEqual(update);
    expect(store.loading()).toBeFalse();
  });

  it('should set theme', () => {
    store.setTheme('DARK');
    expect(store.theme()).toBe('DARK');
    expect(document.documentElement.className).toBe('DARK');
  });

  it('should resolve AUTO theme to DARK', () => {
    spyOn(window, 'matchMedia').and.returnValue({
      matches: true,
    } as MediaQueryList);
    store.setTheme('AUTO');
    expect(document.documentElement.className).toBe('DARK');
  });

  it('should resolve AUTO theme to LIGHT', () => {
    spyOn(window, 'matchMedia').and.returnValue({
      matches: false,
    } as MediaQueryList);
    store.setTheme('AUTO');
    expect(document.documentElement.className).toBe('LIGHT');
  });
});
