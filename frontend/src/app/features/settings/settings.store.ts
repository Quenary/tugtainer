import {
  patchState,
  signalStore,
  type,
  withHooks,
  withMethods,
  withState,
} from '@ngrx/signals';
import {
  entityConfig,
  setEntities,
  updateEntity,
  withEntities,
} from '@ngrx/signals/entities';
import {
  ISetting,
  ISettingUpdate,
  ITestNotificationRequestBody,
} from './settings.interface';
import { inject } from '@angular/core';
import { SettingsApiService } from './settings-api.service';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { pipe, switchMap, tap } from 'rxjs';
import { tapResponse } from '@ngrx/operators';
import { ToastService } from 'src/app/core/services/toast.service';

interface ISettingsStore {
  loading: boolean;
  timezones: string[];
}

const settingsEntityConfig = entityConfig({
  entity: type<ISetting>(),
  selectId: (item) => item.key,
});

export const SettingsStore = signalStore(
  { providedIn: 'root' },
  withEntities(settingsEntityConfig),
  withState<ISettingsStore>({
    loading: false,
    timezones: [],
  }),
  withMethods((store) => {
    const settingsApiService = inject(SettingsApiService);
    const toastService = inject(ToastService);

    return {
      loadList: rxMethod<void>(
        pipe(
          tap(() => patchState(store, { loading: true })),
          switchMap(() =>
            settingsApiService.list().pipe(
              tapResponse({
                next: (list) =>
                  patchState(store, setEntities(list, settingsEntityConfig)),
                error: (error) => toastService.error(error),
                finalize: () => patchState(store, { loading: false }),
              }),
            ),
          ),
        ),
      ),
      loadTimezones: rxMethod<void>(
        pipe(
          tap(() => patchState(store, { loading: true })),
          switchMap(() =>
            settingsApiService.getAvailableTimezones().pipe(
              tapResponse({
                next: (timezones) => patchState(store, { timezones }),
                error: (error) => toastService.error(error),
                finalize: () => patchState(store, { loading: false }),
              }),
            ),
          ),
        ),
      ),
      testNotification: rxMethod<ITestNotificationRequestBody>(
        pipe(
          tap(() => patchState(store, { loading: true })),
          switchMap((body) =>
            settingsApiService.test_notification(body).pipe(
              tapResponse({
                next: () => toastService.success(),
                error: (error) => toastService.error(error),
                finalize: () => patchState(store, { loading: false }),
              }),
            ),
          ),
        ),
      ),
      change: rxMethod<{ entities: ISettingUpdate[] }>(
        pipe(
          tap(() => patchState(store, { loading: true })),
          switchMap(({ entities }) =>
            settingsApiService.change(entities).pipe(
              tapResponse({
                next: () =>
                  patchState(
                    store,
                    ...entities.map(({ key, value }) =>
                      updateEntity<ISetting>(
                        {
                          id: key,
                          changes: { value },
                        },
                        settingsEntityConfig,
                      ),
                    ),
                  ),
                error: (error) => toastService.error(error),
                finalize: () => patchState(store, { loading: false }),
              }),
            ),
          ),
        ),
      ),
    };
  }),
  withHooks({
    onInit: (store) => {
      store.loadList();
      store.loadTimezones();
    },
  }),
);
