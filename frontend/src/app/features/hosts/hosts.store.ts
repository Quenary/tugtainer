import {
  patchState,
  signalStore,
  withComputed,
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
import { ICreateHost, IHostInfo, IHostStatus } from './hosts.interface';
import { computed, inject } from '@angular/core';
import { HostsApiService } from './hosts-api.service';
import { ToastService } from 'src/app/core/services/toast.service';
import { Observable, pipe, switchMap, tap } from 'rxjs';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { Router } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { tapResponse } from '@ngrx/operators';
import {
  EActionStatus,
  IAllActionProgress,
  IHostActionProgress,
} from '@shared/interfaces/progress.interface';
import { ContainersApiService } from '../containers/containers-api.service';
import { IHostSummary } from '../public/public-interface';
import { PublicApiService } from '../public/public-api.service';
import { HttpErrorResponse } from '@angular/common/http';
import { IHostActionResult } from '@shared/interfaces/check-result.interface';
import { IPruneImageRequestBodySchema } from '../images/images.interface';
import { ImagesApiService } from '../images/images-api.service';
import { DialogService } from 'primeng/dynamicdialog';
import {
  ActionResultDialogComponent,
  IActionResultDialogData,
} from '@shared/components/action-result-dialog/action-result-dialog.component';

interface IHostsStore {
  loading: THostsLoading;
  selectedId: number | null;
  globalActionProgress: IAllActionProgress | null;
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
  progress: IHostActionProgress | null;
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
    globalActionProgress: null,
    updateContainersList: null,
    updateImagesList: null,
  })),
  withComputed((store) => ({
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
      return hosts.some((h) => h.available_updates_count ?? 0 > 0);
    }),
    /**
     * If global action (check/update) is active
     */
    globalActionActive: computed<boolean>(() => {
      const globalACtionProgress = store.globalActionProgress();
      return (
        globalACtionProgress &&
        ![EActionStatus.DONE, EActionStatus.ERROR].includes(
          globalACtionProgress.status,
        )
      );
    }),
  })),
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
        tap(() => patchState(store, { loading: 'loading' })),
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
                    progress: null,
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
              finalize: () => patchState(store, { loading: null }),
            }),
          ),
        ),
      ),
    );

    const loadSummary = rxMethod<void>(
      pipe(
        tap(() => patchState(store, { loading: 'loading' })),
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
              finalize: () => patchState(store, { loading: null }),
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
            { loading: 'loading' },
            updateEntity({
              id: hostId,
              changes: { status: null },
            }),
          ),
        ),
        switchMap(({ hostId }) =>
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
                  { loading: null },
                );
              },
            }),
          ),
        ),
      ),
    );

    function createActionMethod(
      apiCall: () => Observable<string>,
      loading: Extract<THostsLoading, 'check' | 'update'>,
    ) {
      return rxMethod<void>(
        pipe(
          tap(() => patchState(store, { globalActionProgress: null, loading })),
          switchMap(() =>
            apiCall().pipe(
              tap(() =>
                toastService.success(
                  translateService.instant('GENERAL.IN_PROGRESS'),
                ),
              ),
              switchMap((cacheId) =>
                containersApiService.watchProgress<IAllActionProgress>(cacheId),
              ),
              tapResponse({
                next: (globalActionProgress) => {
                  patchState(store, { globalActionProgress });
                  if (globalActionProgress.result) {
                    openActionResultDialog(
                      Object.values(globalActionProgress.result),
                      null,
                    );
                  }
                },
                error: (error) => {
                  toastService.error(error);
                },
                finalize: () => {
                  patchState(store, { loading: null });
                  loadList();
                  _updateContainersList();
                  _updateImagesList();
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
                changes: {
                  progress: null,
                  loading,
                },
              }),
            ),
          ),
          switchMap(({ id }) =>
            apiCall(id).pipe(
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
                next: (progress) => {
                  patchState(
                    store,
                    updateEntity({
                      id,
                      changes: { progress },
                    }),
                  );
                  if (progress.result) {
                    openActionResultDialog([progress.result], null);
                  }
                },
                error: (error) => {
                  toastService.error(error);
                },
                finalize: () => {
                  patchState(
                    store,
                    updateEntity({
                      id,
                      changes: { loading: null },
                    }),
                  );
                  loadList();
                  _updateContainersList();
                  _updateImagesList();
                },
              }),
            ),
          ),
        ),
      );
    }

    const openActionResultDialog = (
      results: IHostActionResult[],
      pruneResult: string | null,
    ) => {
      dialogService.open<ActionResultDialogComponent, IActionResultDialogData>(
        ActionResultDialogComponent,
        {
          closeOnEscape: true,
          closable: true,
          header: translateService.instant('ACTIONS.ACTION_COMPLETED'),
          data: {
            results,
            pruneResult,
          },
        },
      );
    };

    return {
      select: (selectedId: number | null) => patchState(store, { selectedId }),
      loadList,
      loadSummary,
      loadStatusOf,
      create: rxMethod<{ body: ICreateHost }>(
        pipe(
          tap(() => patchState(store, { loading: 'loading' })),
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
                      progress: null,
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
                finalize: () => patchState(store, { loading: null }),
              }),
            ),
          ),
        ),
      ),
      update: rxMethod<{ id: number; body: ICreateHost }>(
        pipe(
          tap(() => patchState(store, { loading: 'loading' })),
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
                finalize: () => patchState(store, { loading: null }),
              }),
            ),
          ),
        ),
      ),
      delete: rxMethod<{ id: number }>(
        pipe(
          tap(() => patchState(store, { loading: 'loading' })),
          switchMap(({ id }) =>
            hostsApiService.delete(id).pipe(
              tapResponse({
                next: () => {
                  toastService.success(translateService.instant('SUCCESS'));
                  router.navigate(['/hosts'], { replaceUrl: true });
                  patchState(store, removeEntity(id));
                },
                error: (error) => toastService.error(error),
                finalize: () => patchState(store, { loading: null }),
              }),
            ),
          ),
        ),
      ),
      /**
       * Check all containers of all hosts
       */
      checkAll: createActionMethod(
        () => containersApiService.checkAll(),
        'check',
      ),
      /**
       * Update all containers of all hosts
       */
      updateAll: createActionMethod(
        () => containersApiService.updateAll(),
        'update',
      ),
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
          switchMap(({ id, body }) =>
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
                  openActionResultDialog([], pruneResult);
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
       * Open action results dialog
       * @param results
       */
      openActionResultDialog,
    };
  }),
);
