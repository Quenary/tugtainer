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
import {
  IContainerInfo,
  IContainerListItem,
  IContainerPatchBody,
  TControlContainerCommand,
} from './containers.interface';
import { computed, effect, inject, untracked } from '@angular/core';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { EMPTY, mergeMap, Observable, pipe, switchMap, tap } from 'rxjs';
import { ContainersApiService } from './containers-api.service';
import { ToastService } from 'src/app/core/services/toast.service';
import { HostsStore } from '../hosts/hosts.store';
import { tapResponse } from '@ngrx/operators';
import {
  containerJobSlot,
  IContainerJob,
  isContainerBusy,
} from '@shared/interfaces/jobs.interface';
import { TranslateService } from '@ngx-translate/core';

interface IContainersStore {
  loading: boolean;
  selectedNameOrId: string | null;
  selectedInfo: IContainerInfo | null;
  hooksEnabled: boolean;
}

/**
 * Container store entity
 */
export interface IContainerEntity extends IContainerListItem {
  progress?: IContainerJob | null;
  loading?: TContainerEntityLoading;
}

export type TContainerEntityLoading =
  'loading' | 'check' | 'update' | TControlContainerCommand | null;

const containersEntityConfig = entityConfig<IContainerEntity>({
  entity: type<IContainerEntity>(),
  selectId: (item) => item.name,
});

export const ContainersStore = signalStore(
  withEntities(containersEntityConfig),
  withState<IContainersStore>(() => ({
    loading: false,
    selectedNameOrId: null,
    selectedInfo: null,
    hooksEnabled: false,
  })),
  withComputed((store) => {
    const hostsStore = inject(HostsStore);

    return {
      /**
       * Selected container
       */
      selected: computed<IContainerEntity | null>(() => {
        const selectedNameOrId = store.selectedNameOrId();
        const entityMap = store.entityMap();
        const entities = store.entities();
        if (!selectedNameOrId) {
          return null;
        }
        const entity = entityMap[selectedNameOrId];
        if (entity) {
          return entity;
        }
        return (
          entities.find(
            (e) =>
              e.name === selectedNameOrId ||
              e.container_id === selectedNameOrId,
          ) ?? null
        );
      }),
      /**
       * Selected host id
       */
      hostId: computed(() => hostsStore.selectedId()),
      /**
       * Selected host
       */
      host: computed(() => hostsStore.selected()),
      /**
       * Is any container update available
       */
      anyForUpdate: computed(() => {
        const entities = store.entities();
        return entities.some((e) => e.update_available);
      }),
    };
  }),
  withMethods((store) => {
    const containersApiService = inject(ContainersApiService);
    const toastService = inject(ToastService);
    const translateService = inject(TranslateService);
    const hostsStore = inject(HostsStore);

    /**
     * Select container by name, id or id(internal int)
     * @param value
     */
    const select = (selectedNameOrId: string | null) => {
      patchState(store, { selectedNameOrId });
    };

    const loadSelected = rxMethod<void>(
      pipe(
        tap(() => patchState(store, { selectedInfo: null })),
        switchMap(() => {
          const hostId = store.hostId();
          const selectedNameOrId = store.selectedNameOrId();
          if (!selectedNameOrId || !hostId) {
            return EMPTY;
          }
          patchState(store, { loading: true });
          return containersApiService.get(hostId, selectedNameOrId).pipe(
            tapResponse({
              next: (selectedInfo) => patchState(store, { selectedInfo }),
              error: (error) => {
                toastService.error(error);
              },
              finalize: () => {
                patchState(store, { loading: false });
              },
            }),
          );
        }),
      ),
    );

    const loadList = rxMethod<void>(
      pipe(
        tap(() => patchState(store, removeAllEntities())),
        switchMap(() => {
          const hostId = store.hostId();
          if (!hostId) {
            return EMPTY;
          }
          patchState(store, { loading: true });
          return containersApiService.list(hostId).pipe(
            tapResponse({
              next: (list) => {
                const jobState = hostsStore.selected()?.jobState;
                const entities: IContainerEntity[] = list.map((item) => ({
                  ...item,
                  progress: containerJobSlot(jobState, item.name) ?? null,
                  loading: isContainerBusy(jobState, item.name)
                    ? jobState?.current?.kind === 'update'
                      ? 'update'
                      : 'check'
                    : null,
                }));
                patchState(store, setEntities(entities, containersEntityConfig));
              },
              error: (error) => toastService.error(error),
              finalize: () => patchState(store, { loading: false }),
            }),
          );
        }),
      ),
    );

    const loadHooksEnabled = rxMethod<void>(
      pipe(
        switchMap(() =>
          containersApiService.hooksEnabled().pipe(
            tapResponse({
              next: (hooksEnabled) => patchState(store, { hooksEnabled }),
              error: (error) => toastService.error(error),
            }),
          ),
        ),
      ),
    );

    function runNamesAction(
      apiCall: (hostId: number, names: string[]) => Observable<string>,
    ) {
      return rxMethod<{ names: string[] }>(
        pipe(
          mergeMap(({ names }) => {
            const hostId = store.hostId();
            if (!hostId || !names.length) {
              return EMPTY;
            }
            return apiCall(hostId, names).pipe(
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
    }

    const checkContainers = runNamesAction((hostId, names) =>
      containersApiService.checkHost(hostId, names),
    );
    const updateContainers = runNamesAction((hostId, names) =>
      containersApiService.updateHost(hostId, names),
    );

    const reloadEntity = rxMethod<{ containerName: string }>(
      pipe(
        mergeMap(({ containerName }) => {
          const hostId = store.hostId();
          if (!hostId) {
            return EMPTY;
          }

          patchState(
            store,
            updateEntity(
              {
                id: containerName,
                changes: { loading: 'loading' },
              },
              containersEntityConfig,
            ),
          );
          return containersApiService.get(hostId, containerName).pipe(
            tapResponse({
              next: (info) =>
                patchState(
                  store,
                  updateEntity(
                    {
                      id: containerName,
                      changes: info.item,
                    },
                    containersEntityConfig,
                  ),
                ),
              error: (error) => toastService.error(error),
              finalize: () =>
                patchState(
                  store,
                  updateEntity(
                    {
                      id: containerName,
                      changes: {
                        loading: null,
                      },
                    },
                    containersEntityConfig,
                  ),
                ),
            }),
          );
        }),
      ),
    );

    const patchContainer = rxMethod<{
      containerName: string;
      body: IContainerPatchBody;
    }>(
      pipe(
        switchMap(({ containerName, body }) => {
          const hostId = store.hostId();
          if (!hostId) {
            return EMPTY;
          }

          patchState(
            store,
            updateEntity(
              {
                id: containerName,
                changes: {
                  loading: 'loading',
                },
              },
              containersEntityConfig,
            ),
          );
          return containersApiService.patch(hostId, containerName, body).pipe(
            tapResponse({
              next: (info) =>
                patchState(
                  store,
                  updateEntity(
                    {
                      id: containerName,
                      changes: info,
                    },
                    containersEntityConfig,
                  ),
                ),
              error: (error) => toastService.error(error),
              finalize: () =>
                patchState(
                  store,
                  updateEntity(
                    {
                      id: containerName,
                      changes: {
                        loading: null,
                      },
                    },
                    containersEntityConfig,
                  ),
                ),
            }),
          );
        }),
      ),
    );

    const controlContainer = rxMethod<{
      containerName: string;
      command: TControlContainerCommand;
    }>(
      pipe(
        switchMap(({ containerName, command }) => {
          const hostId = store.hostId();
          if (!hostId) {
            return EMPTY;
          }

          patchState(
            store,
            updateEntity(
              {
                id: containerName,
                changes: {
                  loading: command,
                },
              },
              containersEntityConfig,
            ),
          );
          return containersApiService
            .controlContainer(hostId, command, containerName)
            .pipe(
              tapResponse({
                next: (info) => {
                  patchState(
                    store,
                    updateEntity(
                      {
                        id: containerName,
                        changes: info.item,
                      },
                      containersEntityConfig,
                    ),
                  );
                },
                error: (error) => {
                  toastService.error(error);
                },
                finalize: () => {
                  patchState(
                    store,
                    updateEntity(
                      {
                        id: containerName,
                        changes: {
                          loading: null,
                        },
                      },
                      containersEntityConfig,
                    ),
                  );
                },
              }),
            );
        }),
      ),
    );

    return {
      select,
      /**
       * Load selected container info
       */
      loadSelected,
      /**
       * Load container list
       */
      loadList,
      /**
       * Load whether container hooks are enabled on the backend
       */
      loadHooksEnabled,
      /**
       * Reload entity by id
       */
      reloadEntity,
      /**
       * Check specified containers
       */
      checkContainers,
      /**
       * Check specified container
       */
      checkContainer: (args: { containerName: string }) =>
        checkContainers({ names: [args.containerName] }),
      /**
       * Update specified containers
       */
      updateContainers,
      /**
       * Update specified container
       */
      updateContainer: (args: { containerName: string }) =>
        updateContainers({ names: [args.containerName] }),
      /**
       * Patch specified container
       */
      patchContainer,
      /**
       * Control specified container
       */
      controlContainer,
    };
  }),
  withHooks({
    onInit: (store) => {
      const hostsStore = inject(HostsStore);

      store.loadHooksEnabled();

      effect(() => {
        store.hostId();
        patchState(store, removeAllEntities());
      });

      effect(() => {
        store.selectedNameOrId();
        patchState(store, { selectedInfo: null });
      });

      effect(() => {
        const u = hostsStore.updateContainersList();
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
            const isCommandLoading =
              !!entity.loading &&
              entity.loading !== 'check' &&
              entity.loading !== 'update' &&
              entity.loading !== 'loading';
            if (isCommandLoading) {
              if (entity.progress !== (slot ?? null)) {
                patchState(
                  store,
                  updateEntity(
                    {
                      id: entity.name,
                      changes: { progress: slot ?? null },
                    },
                    containersEntityConfig,
                  ),
                );
              }
              continue;
            }
            const loading: TContainerEntityLoading = busy
              ? jobState?.current?.kind === 'update'
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
                  containersEntityConfig,
                ),
              );
            }
          }
        });
      });
    },
  }),
);
