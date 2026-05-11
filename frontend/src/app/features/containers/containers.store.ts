import {
  patchState,
  signalStore,
  type,
  withComputed,
  withHooks,
  withLinkedState,
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
import { computed, effect, inject, linkedSignal } from '@angular/core';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { EMPTY, Observable, pipe, switchMap, tap } from 'rxjs';
import { ContainersApiService } from './containers-api.service';
import { ToastService } from 'src/app/core/services/toast.service';
import { HostsStore } from '../hosts/hosts.store';
import { tapResponse } from '@ngrx/operators';
import {
  EActionStatus,
  IContainerActionProgress,
  IHostActionProgress,
} from '@shared/interfaces/progress.interface';
import { TranslateService } from '@ngx-translate/core';

interface IContainersStore {
  loading: boolean;
  selectedNameOrId: string | null;
  selectedInfo: IContainerInfo | null;
  hostActionProgress: IHostActionProgress | null;
}

/**
 * Container store entity
 */
export interface IContainerEntity extends IContainerListItem {
  progress?: IContainerActionProgress | null;
  loading?: TContainerEntityLoading;
}

export type TContainerEntityLoading =
  | 'loading'
  | 'check'
  | 'update'
  | TControlContainerCommand
  | null;

export const ContainersStore = signalStore(
  withEntities<IContainerEntity>(
    entityConfig({
      entity: type<IContainerEntity>(),
      selectId: (item) => item.name,
    }),
  ),
  withState<IContainersStore>(() => ({
    loading: false,
    selectedNameOrId: null,
    selectedInfo: null,
    hostActionProgress: null,
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
       * Is host check/update action in progress
       */
      hostActionActive: computed(() => {
        const hostActionProgress = store.hostActionProgress();
        return (
          hostActionProgress &&
          ![EActionStatus.DONE, EActionStatus.ERROR].includes(
            hostActionProgress.status,
          )
        );
      }),
      /**
       * Is any container update available
       */
      anyForUpdate: computed(() => {
        const entities = store.entities();
        return entities.some((e) => e.update_available);
      }),
    };
  }),
  withLinkedState((store) => ({
    /**
     * Whether to show host action result dialog,
     * linked signal that may be changed programatically
     */
    hostActionDialogOpened: linkedSignal(() => {
      const hostActionProgress = store.hostActionProgress();
      const hostActionActive = store.hostActionActive();
      return hostActionProgress && !hostActionActive;
    }),
  })),
  withMethods((store) => {
    const containersApiService = inject(ContainersApiService);
    const toastService = inject(ToastService);
    const translateService = inject(TranslateService);

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
              next: (list) => patchState(store, setEntities(list)),
              error: (error) => toastService.error(error),
              finalize: () => patchState(store, { loading: false }),
            }),
          );
        }),
      ),
    );

    function createHostActionMethod(
      apiCall: (hostId: number) => Observable<string>,
    ) {
      return rxMethod<void>(
        pipe(
          tap(() => patchState(store, { hostActionProgress: null })),
          switchMap(() => {
            const hostId = store.hostId();
            if (!hostId) {
              return EMPTY;
            }
            patchState(store, { loading: true });
            return apiCall(hostId).pipe(
              tap(() =>
                toastService.success(
                  translateService.instant('GENERAL.IN_PROGRESS'),
                ),
              ),
              switchMap((cacheId) =>
                containersApiService.watchProgress<IHostActionProgress>(
                  cacheId,
                ),
              ),
              tapResponse({
                next: (hostActionProgress) => {
                  patchState(store, { hostActionProgress });
                },
                error: (error) => {
                  toastService.error(error);
                },
                finalize: () => {
                  patchState(store, { loading: false });
                  loadList();
                },
              }),
            );
          }),
        ),
      );
    }

    function createContainerActionMethod(
      apiCall: (hostId: number, name: string) => Observable<string>,
      loading: Extract<TContainerEntityLoading, 'check' | 'update'>,
    ) {
      return rxMethod<{ id: number }>(
        pipe(
          tap(({ id }) =>
            patchState(
              store,
              updateEntity({
                id,
                changes: {
                  progress: null,
                },
              }),
            ),
          ),
          switchMap(({ id }) => {
            const hostId = store.hostId();
            const entity = store.entityMap()[id];
            if (!hostId || !entity) {
              return EMPTY;
            }
            patchState(
              store,
              updateEntity({
                id,
                changes: {
                  loading,
                },
              }),
            );
            return apiCall(hostId, entity.name).pipe(
              tap(() =>
                toastService.success(
                  translateService.instant('GENERAL.IN_PROGRESS'),
                ),
              ),
              switchMap((cacheId) =>
                containersApiService.watchProgress<IContainerActionProgress>(
                  cacheId,
                ),
              ),
              tapResponse({
                next: (progress) => {
                  patchState(
                    store,
                    updateEntity({
                      id,
                      changes: { progress },
                    }),
                  );
                },
                error: (error) => {
                  toastService.error(error);
                },
                finalize: () => {
                  patchState(
                    store,
                    updateEntity({
                      id,
                      changes: {
                        loading: null,
                      },
                    }),
                  );
                  reloadEntity({ id });
                },
              }),
            );
          }),
        ),
      );
    }

    const reloadEntity = rxMethod<{ id: number }>(
      pipe(
        switchMap(({ id }) => {
          const hostId = store.hostId();
          const entity = store.entityMap()[id];
          if (!entity || !hostId) {
            return EMPTY;
          }
          patchState(
            store,
            updateEntity({
              id,
              changes: { loading: 'loading' },
            }),
          );
          return containersApiService.get(hostId, entity.name).pipe(
            tapResponse({
              next: (info) =>
                patchState(
                  store,
                  updateEntity({
                    id,
                    changes: info.item,
                  }),
                ),
              error: (error) => toastService.error(error),
              finalize: () =>
                patchState(
                  store,
                  updateEntity({
                    id,
                    changes: {
                      loading: null,
                    },
                  }),
                ),
            }),
          );
        }),
      ),
    );

    const patchContainer = rxMethod<{
      id: number;
      body: IContainerPatchBody;
    }>(
      pipe(
        switchMap(({ id, body }) => {
          const hostId = store.hostId();
          const entity = store.entityMap()[id];
          if (!hostId || !entity) {
            return EMPTY;
          }
          patchState(
            store,
            updateEntity({
              id: entity.id,
              changes: {
                loading: 'loading',
              },
            }),
          );
          return containersApiService.patch(hostId, entity.name, body).pipe(
            tapResponse({
              next: (info) =>
                patchState(
                  store,
                  updateEntity({
                    id: info.id,
                    changes: info,
                  }),
                ),
              error: (error) => toastService.error(error),
              finalize: () =>
                patchState(
                  store,
                  updateEntity({
                    id: entity.id,
                    changes: {
                      loading: null,
                    },
                  }),
                ),
            }),
          );
        }),
      ),
    );

    const controlContainer = rxMethod<{
      id: number;
      command: TControlContainerCommand;
    }>(
      pipe(
        switchMap(({ id, command }) => {
          const hostId = store.hostId();
          const entity = store.entityMap()[id];
          if (!hostId || !entity) {
            return EMPTY;
          }
          patchState(
            store,
            updateEntity({
              id: entity.id,
              changes: {
                loading: command,
              },
            }),
          );
          return containersApiService
            .controlContainer(hostId, command, entity.container_id)
            .pipe(
              tapResponse({
                next: (info) => {
                  patchState(
                    store,
                    updateEntity({
                      id: entity.id,
                      changes: info.item,
                    }),
                  );
                },
                error: (error) => {
                  toastService.error(error);
                },
                finalize: () => {
                  patchState(
                    store,
                    updateEntity({
                      id: entity.id,
                      changes: {
                        loading: null,
                      },
                    }),
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
       * Reload entity by id
       */
      reloadEntity,
      /**
       * Check all containers of host
       */
      checkAll: createHostActionMethod((hostId) =>
        containersApiService.checkHost(hostId),
      ),
      /**
       * Update all containers of host
       */
      updateAll: createHostActionMethod((hostId) =>
        containersApiService.updateHost(hostId),
      ),
      /**
       * Check specified container
       */
      checkContainer: createContainerActionMethod(
        (...args) => containersApiService.checkContainer(...args),
        'check',
      ),
      /**
       * Update specified container
       */
      updateContainer: createContainerActionMethod(
        (...args) => containersApiService.updateContainer(...args),
        'update',
      ),
      /**
       * Patch specified container
       */
      patchContainer,
      /**
       * Control specified container
       */
      controlContainer,
      /**
       * Set value of hostActionDialogOpened flag
       * @param hostActionDialog
       * @returns
       */
      setHostActionDialogOpened: (hostActionDialogOpened: boolean) =>
        patchState(store, { hostActionDialogOpened }),
    };
  }),
  withHooks({
    onInit: (store) => {
      effect(() => {
        store.hostId();
        patchState(store, { hostActionProgress: null }, removeAllEntities());
      });

      effect(() => {
        store.selectedNameOrId();
        patchState(store, { selectedInfo: null });
      });
    },
  }),
);
