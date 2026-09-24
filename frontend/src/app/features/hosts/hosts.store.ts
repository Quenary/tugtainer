import {
  patchState,
  signalStore,
  withComputed,
  withHooks,
  withMethods,
  withState,
} from '@ngrx/signals';
import {
  addEntity,
  removeEntity,
  updateEntity,
  upsertEntities,
  withEntities,
} from '@ngrx/signals/entities';
import {
  IHostCreate,
  IHostInfo,
  IHostStatus,
  IHostUpdate,
} from './hosts.interface';
import { computed, effect, inject } from '@angular/core';
import { HostsApiService } from './hosts-api.service';
import { ToastService } from 'src/app/core/services/toast.service';
import { EMPTY, mergeMap, Observable, pipe, switchMap, tap } from 'rxjs';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { tapResponse } from '@ngrx/operators';
import {
  IHostState,
  isHostBusy,
  shouldIncludeHostToJobsDialog,
} from '@shared/interfaces/jobs.interface';
import { ContainersApiService } from '../containers/containers-api.service';
import { IHostSummary } from '../public/public-interface';
import { PublicApiService } from '../public/public-api.service';
import { HttpErrorResponse } from '@angular/common/http';
import { IPruneImageRequestBodySchema } from '../images/images.interface';
import { ImagesApiService } from '../images/images-api.service';
import { DialogService, DynamicDialogRef } from 'primeng/dynamicdialog';
import {
  IJobsProgressDialogSource,
  JobsProgressDialogComponent,
} from '@shared/components/jobs-progress-dialog/jobs-progress-dialog.component';
import { SocketService } from '../../core/services/socket.service';

interface IHostsStore {
  loading: boolean;
  selectedId: number | null;
  /**
   * Update containers list signal
   */
  updateContainersList: Date | null;
  /**
   * Update images list signal
   */
  updateImagesList: Date | null;
}

export interface IHostEntity extends IHostInfo {
  summary: IHostSummary | null;
  status: IHostStatus | null;
  jobState: IHostState | null;
  pruneResult: string | null;
  loading: THostsLoading;
}

export type THostsLoading = 'loading' | 'check' | 'update' | 'prune' | null;

export const HostsStore = signalStore(
  { providedIn: 'root' },
  withEntities<IHostEntity>(),
  withState<IHostsStore>(() => ({
    loading: null,
    selectedId: null,
    updateContainersList: null,
    updateImagesList: null,
  })),
  withComputed((store) => {
    const globalCheckActive = computed<boolean>(() => {
      const hosts = store.entities();
      return hosts.some(
        (h) => h.loading === 'check' || h.jobState?.current?.kind === 'check',
      );
    });

    const globalUpdateActive = computed<boolean>(() => {
      const hosts = store.entities();
      return hosts.some(
        (h) => h.loading === 'update' || h.jobState?.current?.kind === 'update',
      );
    });

    const globalActionActive = computed<boolean>(() => {
      return globalCheckActive() || globalUpdateActive();
    });

    return {
      /**
       * Selected host entity
       */
      selected: computed<IHostEntity | null>(() => {
        const id = store.selectedId();
        const hosts = store.entityMap();
        return hosts[id] ?? null;
      }),
      /**
       * If any host has containers with available updates
       */
      anyForUpdate: computed(() => {
        const hosts = store.entities();
        return hosts.some((h) => (h.available_updates_count ?? 0) > 0);
      }),
      /**
       * If global action (check) is active
       */
      globalCheckActive,
      /**
       * If global action (update) is active
       */
      globalUpdateActive,
      /**
       * If global action (check/update) is active
       */
      globalActionActive,
    };
  }),
  withMethods((store) => {
    const hostsApiService = inject(HostsApiService);
    const toastService = inject(ToastService);
    const router = inject(Router);
    const translateService = inject(TranslateService);
    const containersApiService = inject(ContainersApiService);
    const publicApiService = inject(PublicApiService);
    const imageApiService = inject(ImagesApiService);
    const dialogService = inject(DialogService);

    const _updateContainersList = () =>
      patchState(store, { updateContainersList: new Date() });
    const _updateImagesList = () =>
      patchState(store, { updateImagesList: new Date() });

    const loadList = rxMethod<void>(
      pipe(
        tap(() => patchState(store, { loading: true })),
        switchMap(() =>
          hostsApiService.list().pipe(
            tapResponse({
              next: (list) => {
                const oldEntities = store.entityMap();
                const entities = list.map<IHostEntity>((item) => ({
                  // Preserve extra data from old entity
                  ...(oldEntities[item.id] ?? {
                    summary: null,
                    status: null,
                    jobState: null,
                    pruneResult: null,
                    loading: null,
                  }),
                  ...item,
                }));
                patchState(store, upsertEntities(entities));
                loadSummary();
                entities
                  .filter((e) => e.enabled)
                  .forEach((e) => {
                    loadStatusOf({ hostId: e.id });
                  });
              },
              error: (error) => toastService.error(error),
              finalize: () => patchState(store, { loading: false }),
            }),
          ),
        ),
      ),
    );

    const loadSummary = rxMethod<void>(
      pipe(
        tap(() => patchState(store, { loading: true })),
        switchMap(() =>
          publicApiService.getSummary().pipe(
            tapResponse({
              next: (summary) => {
                patchState(
                  store,
                  ...summary.map((item) =>
                    updateEntity<IHostEntity>({
                      id: item.host_id,
                      changes: {
                        summary: item,
                      },
                    }),
                  ),
                );
              },
              error: (error) => {
                toastService.error(error);
              },
              finalize: () => patchState(store, { loading: false }),
            }),
          ),
        ),
      ),
    );

    const loadStatusOf = rxMethod<{ hostId: number }>(
      pipe(
        tap(({ hostId }) =>
          patchState(
            store,
            { loading: true },
            updateEntity({
              id: hostId,
              changes: { status: null },
            }),
          ),
        ),
        mergeMap(({ hostId }) =>
          hostsApiService.status(hostId).pipe(
            tapResponse({
              next: (status) =>
                patchState(
                  store,
                  updateEntity({
                    id: hostId,
                    changes: { status },
                  }),
                  { loading: null },
                ),
              error: (error: HttpErrorResponse) => {
                toastService.error(error);
                patchState(
                  store,
                  updateEntity({
                    id: hostId,
                    changes: {
                      status: {
                        id: hostId,
                        ok: false,
                        err: error?.message,
                      },
                    },
                  }),
                  { loading: false },
                );
              },
            }),
          ),
        ),
      ),
    );

    function createActionMethod(apiCall: () => Observable<void>) {
      return rxMethod<void>(
        pipe(
          tap(() => patchState(store, { loading: true })),
          switchMap(() =>
            apiCall().pipe(
              tapResponse({
                next: () => {
                  toastService.success(
                    translateService.instant('GENERAL.IN_PROGRESS'),
                  );
                  openJobProgressDialog({ global: true });
                },
                error: (error) => {
                  toastService.error(error);
                },
                finalize: () => {
                  patchState(store, { loading: false });
                },
              }),
            ),
          ),
        ),
      );
    }

    function createHostActionMethod(
      apiCall: (hostId: number) => Observable<string>,
      loading: Extract<THostsLoading, 'check' | 'update'>,
    ) {
      return rxMethod<{ id: number }>(
        pipe(
          tap(({ id }) =>
            patchState(
              store,
              updateEntity({
                id,
                changes: { loading },
              }),
            ),
          ),
          mergeMap(({ id }) =>
            apiCall(id).pipe(
              tap(() =>
                toastService.success(
                  translateService.instant('GENERAL.IN_PROGRESS'),
                ),
              ),
              tapResponse({
                next: () => undefined,
                error: (error) => {
                  toastService.error(error);
                  patchState(
                    store,
                    updateEntity({
                      id,
                      changes: { loading: null },
                    }),
                  );
                },
              }),
            ),
          ),
        ),
      );
    }

    const applyHostState = (hostId: number, jobState: IHostState | null) => {
      const entity = store.entityMap()[hostId];
      if (!entity) {
        return;
      }
      const prevActive = isHostBusy(entity.jobState);
      const nextActive = isHostBusy(jobState);
      let loading = entity.loading;
      if (loading !== 'prune') {
        if (nextActive) {
          loading = jobState?.current?.kind === 'update' ? 'update' : 'check';
        } else if (jobState && (loading === 'check' || loading === 'update')) {
          loading = null;
        }
      }
      patchState(
        store,
        updateEntity({
          id: hostId,
          changes: { jobState, loading },
        }),
      );
      if (prevActive && !nextActive) {
        if (jobState?.completed?.length) {
          openJobProgressDialog({ hostId });
        }
        loadList();
        _updateContainersList();
        _updateImagesList();
      }
    };

    const loadHostState = rxMethod<number | null>(
      pipe(
        switchMap((hostId) => {
          if (!hostId) {
            return EMPTY;
          }
          return containersApiService.hostState(hostId).pipe(
            tapResponse({
              next: (jobState) => applyHostState(hostId, jobState),
              error: () => undefined,
            }),
          );
        }),
      ),
    );

    const socketService = inject(SocketService);
    const watchSocketProgress = rxMethod<void>(
      pipe(
        switchMap(() =>
          socketService.jobProgress$.pipe(
            tap((event) => {
              applyHostState(event.host_id, event.state);
            }),
          ),
        ),
      ),
    );

    let progressDialogRef: DynamicDialogRef | null = null;

    const openJobProgressDialog = (source: {
      hostId?: number;
      global?: boolean;
    }) => {
      if (progressDialogRef) {
        return;
      }
      const ref = dialogService.open<
        JobsProgressDialogComponent,
        IJobsProgressDialogSource
      >(JobsProgressDialogComponent, {
        closeOnEscape: true,
        closable: true,
        header: translateService.instant('ACTIONS.PROGRESS'),
        data: {
          read: () => {
            if (source.global) {
              const entities = store.entities();
              const hosts = [];
              for (const host of entities) {
                if (
                  shouldIncludeHostToJobsDialog(host.jobState, host.pruneResult)
                ) {
                  hosts.push({
                    hostId: host.id,
                    hostName: host.name,
                    jobState: host.jobState ?? null,
                    pruneResult: host.pruneResult ?? null,
                  });
                }
              }
              return { hosts };
            }
            const entity =
              source.hostId != null ? store.entityMap()[source.hostId] : null;
            return {
              hosts: entity
                ? [
                    {
                      hostId: entity.id,
                      hostName: entity.name,
                      jobState: entity.jobState ?? null,
                      pruneResult: entity.pruneResult ?? null,
                    },
                  ]
                : [],
            };
          },
        },
      });
      if (!ref) {
        return;
      }
      progressDialogRef = ref;
      progressDialogRef.onClose.subscribe(() => {
        progressDialogRef = null;
      });
    };

    return {
      select: (selectedId: number | null) => patchState(store, { selectedId }),
      loadList,
      loadSummary,
      loadStatusOf,
      create: rxMethod<{ body: IHostCreate }>(
        pipe(
          tap(() => patchState(store, { loading: true })),
          switchMap(({ body }) =>
            hostsApiService.create(body).pipe(
              tapResponse({
                next: (info) => {
                  patchState(
                    store,
                    addEntity<IHostEntity>({
                      ...info,
                      summary: null,
                      status: null,
                      jobState: null,
                      pruneResult: null,
                      loading: null,
                    }),
                    { selectedId: info.id },
                  );
                  router.navigate([`/hosts/${info.id}`], { replaceUrl: true });
                  if (info.enabled) {
                    loadSummary();
                    loadStatusOf({ hostId: info.id });
                  }
                },
                error: (error) => toastService.error(error),
                finalize: () => patchState(store, { loading: false }),
              }),
            ),
          ),
        ),
      ),
      update: rxMethod<{ id: number; body: IHostUpdate }>(
        pipe(
          tap(() => patchState(store, { loading: true })),
          switchMap(({ id, body }) =>
            hostsApiService.update(id, body).pipe(
              tapResponse({
                next: (info) => {
                  patchState(
                    store,
                    updateEntity<IHostEntity>({
                      id: info.id,
                      changes: { ...info, summary: null, status: null },
                    }),
                  );
                  if (info.enabled) {
                    loadSummary();
                    loadStatusOf({ hostId: info.id });
                  }
                },
                error: (error) => toastService.error(error),
                finalize: () => patchState(store, { loading: false }),
              }),
            ),
          ),
        ),
      ),
      delete: rxMethod<{ id: number }>(
        pipe(
          tap(() => patchState(store, { loading: true })),
          switchMap(({ id }) =>
            hostsApiService.delete(id).pipe(
              tapResponse({
                next: () => {
                  toastService.success(translateService.instant('SUCCESS'));
                  router.navigate(['/hosts'], { replaceUrl: true });
                  patchState(store, removeEntity(id));
                },
                error: (error) => toastService.error(error),
                finalize: () => patchState(store, { loading: false }),
              }),
            ),
          ),
        ),
      ),
      /**
       * Check all containers of all hosts
       */
      checkAll: createActionMethod(() => containersApiService.checkAll()),
      /**
       * Update all containers of all hosts
       */
      updateAll: createActionMethod(() => containersApiService.updateAll()),
      /**
       * Check all containers of host
       */
      checkHost: createHostActionMethod(
        (id) => containersApiService.checkHost(id),
        'check',
      ),
      /**
       * Update all containers of host
       */
      updateHost: createHostActionMethod(
        (id) => containersApiService.updateHost(id),
        'update',
      ),
      /**
       * Prune images of host
       */
      pruneHost: rxMethod<{ id: number; body: IPruneImageRequestBodySchema }>(
        pipe(
          tap(({ id }) =>
            patchState(
              store,
              updateEntity({
                id,
                changes: {
                  pruneResult: null,
                  loading: 'prune',
                },
              }),
            ),
          ),
          mergeMap(({ id, body }) =>
            imageApiService.prune(id, body).pipe(
              tapResponse({
                next: (pruneResult) => {
                  patchState(
                    store,
                    updateEntity({
                      id,
                      changes: {
                        pruneResult,
                      },
                    }),
                  );
                  openJobProgressDialog({ hostId: id });
                },
                error: (error) => toastService.error(error),
                finalize: () => {
                  patchState(
                    store,
                    updateEntity({ id, changes: { loading: null } }),
                  );
                  _updateImagesList();
                },
              }),
            ),
          ),
        ),
      ),
      /**
       * Open queued / completed host jobs dialog
       */
      openJobProgressDialog,
      /**
       * Load unified host job state while a host is selected
       */
      loadHostState,
      watchSocketProgress,
    };
  }),
  withHooks({
    onInit: (store) => {
      effect(() => {
        store.loadHostState(store.selectedId());
      });
      store.watchSocketProgress();
    },
  }),
);
