import {
  patchState,
  signalStore,
  withHooks,
  withMethods,
  withState,
} from '@ngrx/signals';
import {
  IsUpdateAvailableResponseBody,
  IVersion,
} from './features/public/public-interface';
import { inject } from '@angular/core';
import { AuthApiService } from './features/auth/auth-api.service';
import { ToastService } from './core/services/toast.service';
import { PublicApiService } from './features/public/public-api.service';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { pipe, switchMap, tap } from 'rxjs';
import { tapResponse } from '@ngrx/operators';
import { EStorageKey } from './app.enums';

interface IAppStore {
  loading: boolean;
  isAuthDisabled: boolean;
  version: IVersion;
  update: IsUpdateAvailableResponseBody | null;
  theme: TAppTheme;
}

export type TAppTheme = 'AUTO' | 'LIGHT' | 'DARK' | null | undefined;

export const AppStore = signalStore(
  { providedIn: 'root' },
  withState<IAppStore>({
    loading: false,
    isAuthDisabled: false,
    version: { image_version: 'unknown' },
    update: null,
    theme: null,
  }),
  withMethods((store) => {
    const authApiService = inject(AuthApiService);
    const publicApiService = inject(PublicApiService);
    const toastService = inject(ToastService);

    return {
      loadIsAuthDisabled: rxMethod<void>(
        pipe(
          tap(() => patchState(store, { loading: true })),
          switchMap(() =>
            authApiService.isDisabled().pipe(
              tapResponse({
                next: (isAuthDisabled) => patchState(store, { isAuthDisabled }),
                error: (error) => {
                  toastService.error(error);
                },
                finalize: () => patchState(store, { loading: false }),
              }),
            ),
          ),
        ),
      ),
      loadVersion: rxMethod<void>(
        pipe(
          tap(() => patchState(store, { loading: true })),
          switchMap(() =>
            publicApiService.getVersion().pipe(
              tapResponse({
                next: (version) => patchState(store, { version }),
                error: (error) => console.log(error),
                finalize: () => patchState(store, { loading: false }),
              }),
            ),
          ),
        ),
      ),
      loadUpdate: rxMethod<void>(
        pipe(
          tap(() => patchState(store, { loading: true })),
          switchMap(() =>
            publicApiService.isUpdateAvailable().pipe(
              tapResponse({
                next: (update) => patchState(store, { update }),
                error: (error) => console.log(error),
                finalize: () => patchState(store, { loading: false }),
              }),
            ),
          ),
        ),
      ),
      setTheme: (theme: TAppTheme) => {
        patchState(store, { theme });
        localStorage.setItemJson(EStorageKey.THEME, theme);
        if (theme == 'AUTO') {
          const isDarkMode =
            window.matchMedia &&
            window.matchMedia('(prefers-color-scheme: dark)').matches;
          theme = isDarkMode ? 'DARK' : 'LIGHT';
        }
        document.documentElement.className = theme;
      },
    };
  }),
  withHooks({
    onInit: (store) => {
      store.loadIsAuthDisabled();
      store.loadUpdate();
      store.loadVersion();
      store.setTheme(localStorage.getItemJson(EStorageKey.THEME) || 'AUTO');
    },
  }),
);
