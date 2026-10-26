import { inject } from '@angular/core';
import { patchState, signalStore, withMethods, withState } from '@ngrx/signals';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { tapResponse } from '@ngrx/operators';
import { TranslateService } from '@ngx-translate/core';
import {
  catchError,
  exhaustMap,
  filter,
  of,
  pipe,
  switchMap,
  take,
  tap,
  timer,
} from 'rxjs';
import { ToastService } from 'src/app/core/services/toast.service';
import { PageReloadService } from 'src/app/core/services/page-reload.service';
import { EStorageKey } from 'src/app/app.enums';
import { SelfUpdateApiService } from './self-update-api.service';
import {
  FINAL_SELF_UPDATE_STATUSES,
  ISelfUpdateState,
} from './self-update.interface';

export const SELF_UPDATE_POLL_INTERVAL_MS = 3000;

interface ISelfUpdateStore {
  loading: boolean;
  allowed: boolean;
  state: ISelfUpdateState | null;
  /**
   * Started from this tab, waiting for the app to come back
   */
  waiting: boolean;
}

const isFinal = (state: ISelfUpdateState | null | undefined): boolean =>
  !!state && FINAL_SELF_UPDATE_STATUSES.includes(state.status);

const getPending = (): boolean => {
  try {
    return !!sessionStorage.getItem(EStorageKey.SELF_UPDATE_PENDING);
  } catch {
    return false;
  }
};

const setPending = (pending: boolean): void => {
  try {
    if (pending) {
      sessionStorage.setItem(EStorageKey.SELF_UPDATE_PENDING, '1');
    } else {
      sessionStorage.removeItem(EStorageKey.SELF_UPDATE_PENDING);
    }
  } catch {
    // Storage unavailable, the result is still shown in the dialog
  }
};

export const SelfUpdateStore = signalStore(
  { providedIn: 'root' },
  withState<ISelfUpdateStore>({
    loading: false,
    allowed: false,
    state: null,
    waiting: false,
  }),
  withMethods((store) => {
    const selfUpdateApiService = inject(SelfUpdateApiService);
    const toastService = inject(ToastService);
    const translateService = inject(TranslateService);
    const pageReloadService = inject(PageReloadService);

    const showResult = (state: ISelfUpdateState): void => {
      const summary = translateService.instant(
        `UPDATE_DIALOGUE.SELF_UPDATE_STATUS.${state.status.toUpperCase()}`,
      );
      if (state.status === 'succeeded') {
        const from = state.old_version ?? state.old_image_id;
        const to = state.new_version ?? state.new_image_id;
        toastService.success(summary, `${from} -> ${to}`);
        return;
      }
      toastService.error(state.error, summary);
    };

    /**
     * Poll until the result is final, then reload the page.
     * The app is unavailable while its container is replaced,
     * so errors are expected and ignored.
     */
    const waitForResult = rxMethod<void>(
      pipe(
        tap(() => patchState(store, { waiting: true })),
        switchMap(() =>
          timer(
            SELF_UPDATE_POLL_INTERVAL_MS,
            SELF_UPDATE_POLL_INTERVAL_MS,
          ).pipe(
            exhaustMap(() =>
              selfUpdateApiService.getStatus().pipe(catchError(() => of(null))),
            ),
            filter((res) => isFinal(res?.state)),
            take(1),
          ),
        ),
        tap(() => pageReloadService.reload()),
      ),
    );

    return {
      loadStatus: rxMethod<void>(
        pipe(
          tap(() => patchState(store, { loading: true })),
          switchMap(() =>
            selfUpdateApiService.getStatus().pipe(
              tapResponse({
                next: ({ allowed, state }) =>
                  patchState(store, { allowed, state }),
                error: (error) => toastService.error(error),
                finalize: () => patchState(store, { loading: false }),
              }),
            ),
          ),
        ),
      ),
      start: rxMethod<void>(
        pipe(
          tap(() => patchState(store, { loading: true })),
          switchMap(() =>
            selfUpdateApiService.start().pipe(
              tapResponse({
                next: (state) => {
                  setPending(true);
                  patchState(store, { state });
                  waitForResult();
                },
                error: (error) => toastService.error(error),
                finalize: () => patchState(store, { loading: false }),
              }),
            ),
          ),
        ),
      ),
      /**
       * Show the result of a self-update started from this tab,
       * after the page reload or the next sign-in.
       */
      showPendingResult: rxMethod<void>(
        pipe(
          filter(() => getPending() && !store.waiting()),
          switchMap(() =>
            selfUpdateApiService.getStatus().pipe(
              tapResponse({
                next: ({ allowed, state }) => {
                  patchState(store, { allowed, state });
                  if (!state) {
                    setPending(false);
                  } else if (isFinal(state)) {
                    setPending(false);
                    showResult(state);
                  } else {
                    waitForResult();
                  }
                },
                error: (error) => console.error(error),
              }),
            ),
          ),
        ),
      ),
    };
  }),
);
