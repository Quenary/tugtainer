import { TestBed } from '@angular/core/testing';
import { PendingTasks } from '@angular/core';
import { provideTranslateService } from '@ngx-translate/core';
import { of, Subject, throwError } from 'rxjs';
import { Mocked } from 'vitest';
import { ToastService } from 'src/app/core/services/toast.service';
import { PageReloadService } from 'src/app/core/services/page-reload.service';
import { EStorageKey } from 'src/app/app.enums';
import { getToastServiceMock } from '@testing/mocks/toast-service.mock';
import { PublicApiService } from 'src/app/features/public/public-api.service';
import { SelfUpdateApiService } from './self-update-api.service';
import {
  ISelfUpdateState,
  ISelfUpdateStatusResponse,
  TSelfUpdateStatus,
} from './self-update.interface';
import {
  SELF_UPDATE_POLL_INTERVAL_MS,
  SELF_UPDATE_WAIT_TIMEOUT_MS,
  SelfUpdateStore,
} from './self-update.store';

const makeState = (
  status: TSelfUpdateStatus,
  patch: Partial<ISelfUpdateState> = {},
): ISelfUpdateState => ({
  status,
  container_name: 'tugtainer',
  old_container_id: 'old',
  new_container_id: null,
  helper_container_name: 'tugtainer-self-update',
  old_image_id: 'sha256:old',
  new_image_id: 'sha256:new',
  old_version: '1.0.0',
  new_version: '1.1.0',
  error: null,
  warnings: [],
  started_at: '2026-10-26T12:00:00Z',
  finished_at: null,
  ...patch,
});

const response = (
  state: ISelfUpdateState | null,
  allowed = true,
): ISelfUpdateStatusResponse => ({ allowed, state });

describe('SelfUpdateStore', () => {
  let store: InstanceType<typeof SelfUpdateStore>;
  let apiMock: Mocked<Pick<SelfUpdateApiService, 'getStatus' | 'start'>>;
  let toastServiceMock: Mocked<ToastService>;
  let reloadMock: { reload: ReturnType<typeof vi.fn> };
  let publicApiMock: Mocked<Pick<PublicApiService, 'getHealth'>>;

  const down = () => throwError(() => new Error('502'));

  beforeEach(() => {
    sessionStorage.clear();
    apiMock = { getStatus: vi.fn(), start: vi.fn() };
    publicApiMock = { getHealth: vi.fn().mockReturnValue(of('OK')) };
    toastServiceMock = getToastServiceMock();
    reloadMock = { reload: vi.fn() };

    TestBed.configureTestingModule({
      providers: [
        SelfUpdateStore,
        PendingTasks,
        provideTranslateService(),
        { provide: SelfUpdateApiService, useValue: apiMock },
        { provide: ToastService, useValue: toastServiceMock },
        { provide: PageReloadService, useValue: reloadMock },
        { provide: PublicApiService, useValue: publicApiMock },
      ],
    });

    store = TestBed.inject(SelfUpdateStore);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  describe('loadStatus', () => {
    it('loads', () => {
      apiMock.getStatus.mockReturnValue(of(response(null, true)));

      store.loadStatus();

      expect(store.allowed()).toBe(true);
      expect(store.state()).toBeNull();
    });

    it('shows error', () => {
      const error = new Error('Test');
      apiMock.getStatus.mockReturnValue(throwError(() => error));

      store.loadStatus();

      expect(toastServiceMock.error).toHaveBeenCalledWith(error);
      expect(store.loading()).toBe(false);
    });
  });

  describe('start', () => {
    it('reloads when the app is back after the restart', () => {
      vi.useFakeTimers();
      apiMock.start.mockReturnValue(of(makeState('pending')));
      apiMock.getStatus.mockReturnValue(of(response(makeState('running'))));
      publicApiMock.getHealth
        .mockReturnValueOnce(of('OK'))
        .mockReturnValueOnce(down())
        .mockReturnValueOnce(down());

      store.start();

      expect(store.waiting()).toBe(true);
      expect(sessionStorage.getItem(EStorageKey.SELF_UPDATE_PENDING)).toBe('1');

      // Old app still running, then down twice
      vi.advanceTimersByTime(SELF_UPDATE_POLL_INTERVAL_MS * 3);
      expect(reloadMock.reload).not.toHaveBeenCalled();
      expect(apiMock.getStatus).toHaveBeenCalledTimes(1);

      vi.advanceTimersByTime(SELF_UPDATE_POLL_INTERVAL_MS);

      expect(reloadMock.reload).toHaveBeenCalledTimes(1);
      // The status is not polled after the restart
      expect(apiMock.getStatus).toHaveBeenCalledTimes(1);
    });

    it('reloads when the status is rejected by the new instance', () => {
      vi.useFakeTimers();
      apiMock.start.mockReturnValue(of(makeState('pending')));
      apiMock.getStatus.mockReturnValue(throwError(() => new Error('401')));

      store.start();

      vi.advanceTimersByTime(SELF_UPDATE_POLL_INTERVAL_MS);
      expect(reloadMock.reload).not.toHaveBeenCalled();

      vi.advanceTimersByTime(SELF_UPDATE_POLL_INTERVAL_MS);

      expect(reloadMock.reload).toHaveBeenCalledTimes(1);
      expect(apiMock.getStatus).toHaveBeenCalledTimes(1);
    });

    it('reloads on a final state without a restart', () => {
      vi.useFakeTimers();
      const status$ = new Subject<ISelfUpdateStatusResponse>();
      apiMock.start.mockReturnValue(of(makeState('pending')));
      apiMock.getStatus.mockReturnValueOnce(of(response(makeState('running'))));
      apiMock.getStatus.mockReturnValueOnce(status$);

      store.start();

      vi.advanceTimersByTime(SELF_UPDATE_POLL_INTERVAL_MS * 2);
      expect(reloadMock.reload).not.toHaveBeenCalled();

      status$.next(response(makeState('aborted')));

      expect(reloadMock.reload).toHaveBeenCalledTimes(1);
    });

    it('stops waiting after the timeout', () => {
      vi.useFakeTimers();
      apiMock.start.mockReturnValue(of(makeState('pending')));
      publicApiMock.getHealth.mockReturnValue(down());

      store.start();

      vi.advanceTimersByTime(SELF_UPDATE_WAIT_TIMEOUT_MS);

      expect(reloadMock.reload).not.toHaveBeenCalled();
      expect(store.waiting()).toBe(false);
      expect(toastServiceMock.error).toHaveBeenCalledWith(
        'UPDATE_DIALOGUE.SELF_UPDATE_TIMEOUT',
      );
      // The result is shown on the next load
      expect(sessionStorage.getItem(EStorageKey.SELF_UPDATE_PENDING)).toBe('1');
    });

    it('shows error and does not wait', () => {
      const error = new Error('409');
      apiMock.start.mockReturnValue(throwError(() => error));

      store.start();

      expect(toastServiceMock.error).toHaveBeenCalledWith(error);
      expect(store.waiting()).toBe(false);
      expect(
        sessionStorage.getItem(EStorageKey.SELF_UPDATE_PENDING),
      ).toBeNull();
    });
  });

  describe('showPendingResult', () => {
    it('does nothing without a pending self-update', () => {
      store.showPendingResult();

      expect(apiMock.getStatus).not.toHaveBeenCalled();
    });

    it('shows success once', () => {
      sessionStorage.setItem(EStorageKey.SELF_UPDATE_PENDING, '1');
      apiMock.getStatus.mockReturnValue(of(response(makeState('succeeded'))));

      store.showPendingResult();
      store.showPendingResult();

      expect(toastServiceMock.success).toHaveBeenCalledTimes(1);
      expect(toastServiceMock.success).toHaveBeenCalledWith(
        'UPDATE_DIALOGUE.SELF_UPDATE_STATUS.SUCCEEDED',
        '1.0.0 -> 1.1.0',
      );
      expect(
        sessionStorage.getItem(EStorageKey.SELF_UPDATE_PENDING),
      ).toBeNull();
    });

    it('shows the error of a rollback', () => {
      sessionStorage.setItem(EStorageKey.SELF_UPDATE_PENDING, '1');
      apiMock.getStatus.mockReturnValue(
        of(response(makeState('rolled_back', { error: 'unhealthy' }))),
      );

      store.showPendingResult();

      expect(toastServiceMock.error).toHaveBeenCalledWith(
        'unhealthy',
        'UPDATE_DIALOGUE.SELF_UPDATE_STATUS.ROLLED_BACK',
      );
    });

    it('keeps waiting while in progress', () => {
      sessionStorage.setItem(EStorageKey.SELF_UPDATE_PENDING, '1');
      apiMock.getStatus.mockReturnValue(of(response(makeState('running'))));

      store.showPendingResult();

      expect(store.waiting()).toBe(true);
      expect(toastServiceMock.success).not.toHaveBeenCalled();
      expect(sessionStorage.getItem(EStorageKey.SELF_UPDATE_PENDING)).toBe('1');
    });
  });
});
