import {
  patchState,
  signalStore,
  type,
  withComputed,
  withHooks,
  withMethods,
  withState,
} from '@ngrx/signals';
import {
  entityConfig,
  removeAllEntities,
  setEntities,
  updateEntity,
  withEntities,
} from '@ngrx/signals/entities';
import { computed, effect, inject, untracked } from '@angular/core';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { EMPTY, mergeMap, pipe, switchMap, tap } from 'rxjs';
import { tapResponse } from '@ngrx/operators';
import { ToastService } from 'src/app/core/services/toast.service';
import { TranslateService } from '@ngx-translate/core';
import {
  containerJobSlot,
  IContainerJob,
  isContainerBusy,
} from '@shared/interfaces/jobs.interface';
import { HostsStore } from '../hosts/hosts.store';
import { IServiceListItem, IServicePatchBody } from './services.interface';
import { ServicesApiService } from './services-api.service';

export interface IServiceEntity extends IServiceListItem {
  progress?: IContainerJob | null;
  loading?: 'loading' | 'check' | 'update' | null;
}

interface IServicesStoreState {
  loading: boolean;
  selectedName: string | null;
}

const servicesEntityConfig = entityConfig<IServiceEntity>({
  entity: type<IServiceEntity>(),
  selectId: (item) => item.name,
});

export const ServicesStore = signalStore(
  withEntities(servicesEntityConfig),
  withState<IServicesStoreState>(() => ({
    loading: false,
    selectedName: null,
  })),
  withComputed((store) => {
    const hostsStore = inject(HostsStore);

    return {
      selected: computed<IServiceEntity | null>(() => {
        const name = store.selectedName();
        if (!name) {
          return null;
        }
        return store.entityMap()[name] ?? null;
      }),
      hostId: computed(() => hostsStore.selectedId()),
      host: computed(() => hostsStore.selected()),
      anyForUpdate: computed(() => {
        return store.entities().some((e) => e.update_available);
      }),
    };
  }),
  withMethods((store) => {
    const servicesApiService = inject(ServicesApiService);
    const toastService = inject(ToastService);
    const translateService = inject(TranslateService);
    const hostsStore = inject(HostsStore);

    const select = (selectedName: string | null) => {
      patchState(store, { selectedName });
    };

    const loadList = rxMethod<void>(
      pipe(
        tap(() => patchState(store, removeAllEntities())),
        switchMap(() => {
          const hostId = store.hostId();
          if (!hostId) {
            return EMPTY;
          }
          patchState(store, { loading: true });
          return servicesApiService.list(hostId).pipe(
            tapResponse({
              next: (list) => {
                const jobState = hostsStore.selected()?.jobState;
                const entities: IServiceEntity[] = list.map((item) => ({
                  ...item,
                  progress: containerJobSlot(jobState, item.name) ?? null,
                  loading: isContainerBusy(jobState, item.name)
                    ? jobState?.current?.kind === 'update_services'
                      ? 'update'
                      : 'check'
                    : null,
                }));
                patchState(store, setEntities(entities, servicesEntityConfig));
              },
              error: (error) => toastService.error(error),
              finalize: () => patchState(store, { loading: false }),
            }),
          );
        }),
      ),
    );

    const checkServices = rxMethod<{ names: string[] }>(
      pipe(
        mergeMap(({ names }) => {
          const hostId = store.hostId();
          if (!hostId || !names.length) {
            return EMPTY;
          }
          return servicesApiService.check(hostId, names).pipe(
            tap(() =>
              toastService.success(
                translateService.instant('GENERAL.IN_PROGRESS'),
              ),
            ),
            tapResponse({
              next: () => undefined,
              error: (error) => toastService.error(error),
            }),
          );
        }),
      ),
    );

    const updateServices = rxMethod<{ names: string[] }>(
      pipe(
        mergeMap(({ names }) => {
          const hostId = store.hostId();
          if (!hostId || !names.length) {
            return EMPTY;
          }
          return servicesApiService.update(hostId, names).pipe(
            tap(() =>
              toastService.success(
                translateService.instant('GENERAL.IN_PROGRESS'),
              ),
            ),
            tapResponse({
              next: () => undefined,
              error: (error) => toastService.error(error),
            }),
          );
        }),
      ),
    );

    const patchService = rxMethod<{
      serviceName: string;
      body: IServicePatchBody;
    }>(
      pipe(
        switchMap(({ serviceName, body }) => {
          const hostId = store.hostId();
          if (!hostId) {
            return EMPTY;
          }
          patchState(
            store,
            updateEntity(
              {
                id: serviceName,
                changes: { loading: 'loading' },
              },
              servicesEntityConfig,
            ),
          );
          return servicesApiService.patch(hostId, serviceName, body).pipe(
            tapResponse({
              next: (item) =>
                patchState(
                  store,
                  updateEntity(
                    {
                      id: serviceName,
                      changes: item,
                    },
                    servicesEntityConfig,
                  ),
                ),
              error: (error) => toastService.error(error),
              finalize: () =>
                patchState(
                  store,
                  updateEntity(
                    {
                      id: serviceName,
                      changes: { loading: null },
                    },
                    servicesEntityConfig,
                  ),
                ),
            }),
          );
        }),
      ),
    );

    return {
      select,
      loadList,
      checkServices,
      updateServices,
      patchService,
    };
  }),
  withHooks({
    onInit: (store) => {
      const hostsStore = inject(HostsStore);

      effect(() => {
        store.hostId();
        patchState(store, removeAllEntities());
      });

      effect(() => {
        const u = hostsStore.updateServicesList();
        if (u) {
          untracked(() => {
            store.loadList();
          });
        }
      });

      effect(() => {
        const jobState = hostsStore.selected()?.jobState ?? null;
        store.ids();
        untracked(() => {
          for (const entity of store.entities()) {
            const slot = containerJobSlot(jobState, entity.name);
            const busy = isContainerBusy(jobState, entity.name);
            const loading: 'loading' | 'check' | 'update' | null = busy
              ? jobState?.current?.kind === 'update_services' ||
                jobState?.current?.kind === 'update'
                ? 'update'
                : 'check'
              : entity.loading === 'check' || entity.loading === 'update'
                ? null
                : (entity.loading ?? null);
            if (
              entity.progress !== (slot ?? null) ||
              entity.loading !== loading
            ) {
              patchState(
                store,
                updateEntity(
                  {
                    id: entity.name,
                    changes: { progress: slot ?? null, loading },
                  },
                  servicesEntityConfig,
                ),
              );
            }
          }
        });
      });
    },
  }),
);
