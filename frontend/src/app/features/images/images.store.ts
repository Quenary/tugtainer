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
  withEntities,
} from '@ngrx/signals/entities';
import {
  IImage,
  IImageInspectResult,
  IPruneImageRequestBodySchema,
} from './images.interface';
import { computed, effect, inject } from '@angular/core';
import { ImagesApiService } from './images-api.service';
import { ToastService } from 'src/app/core/services/toast.service';
import { rxMethod } from '@ngrx/signals/rxjs-interop';
import { EMPTY, pipe, switchMap, tap } from 'rxjs';
import { tapResponse } from '@ngrx/operators';
import { HostsStore } from '../hosts/hosts.store';

export type TImagesLoading = 'loading' | 'prune' | null;

interface ImagesState {
  loading: TImagesLoading;
  selectedId: string | null;
  selectedInfo: IImageInspectResult | null;
  pruneResult: string | null;
}

export interface IImageEntity extends IImage {} // eslint-disable-line

export const ImagesStore = signalStore(
  withEntities(
    entityConfig({
      entity: type<IImageEntity>(),
      selectId: (item) => item.id,
    }),
  ),
  withState<ImagesState>(() => ({
    loading: null,
    selectedId: null,
    selectedInfo: null,
    pruneResult: null,
  })),
  withComputed((store) => {
    const hostsStore = inject(HostsStore);

    return {
      /**
       * Selected host id
       */
      hostId: computed(() => hostsStore.selectedId()),
      /**
       * Selected host
       */
      host: computed(() => hostsStore.selected()),
      /**
       * Selected image entity
       */
      selected: computed(() => {
        const selectedId = store.selectedId();
        const entitiesMap = store.entityMap();
        return entitiesMap[selectedId] ?? null;
      }),
    };
  }),
  withMethods((store) => {
    const imagesApiService = inject(ImagesApiService);
    const toastService = inject(ToastService);

    const loadList = rxMethod<void>(
      pipe(
        switchMap(() => {
          const hostId = store.hostId();
          if (!hostId) {
            return EMPTY;
          }
          patchState(store, { loading: 'loading' });
          return imagesApiService.list(hostId).pipe(
            tapResponse({
              next: (list) => patchState(store, setEntities(list)),
              error: (error) => toastService.error(error),
              finalize: () => patchState(store, { loading: null }),
            }),
          );
        }),
      ),
    );

    return {
      /**
       * Select image
       * @param selectedId
       * @returns
       */
      select: (selectedId: string | null) => patchState(store, { selectedId }),
      /**
       * Load list of images
       */
      loadList,
      /**
       * Load selected image inspect info
       */
      loadSelected: rxMethod<void>(
        pipe(
          switchMap(() => {
            const hostId = store.hostId();
            const selectedId = store.selectedId();
            if (!hostId || !selectedId) {
              return EMPTY;
            }
            patchState(store, { loading: 'loading' });
            return imagesApiService.inspect(hostId, selectedId).pipe(
              tapResponse({
                next: (selectedInfo) => patchState(store, { selectedInfo }),
                error: (error) => {
                  toastService.error(error);
                },
                finalize: () => {
                  patchState(store, { loading: null });
                },
              }),
            );
          }),
        ),
      ),
      /**
       * Prune images of selected host
       */
      prune: rxMethod<{ body: IPruneImageRequestBodySchema }>(
        pipe(
          tap(() => patchState(store, { loading: 'prune', pruneResult: null })),
          switchMap(({ body }) =>
            imagesApiService.prune(store.hostId(), body).pipe(
              tapResponse({
                next: (pruneResult) => {
                  patchState(store, { pruneResult });
                },
                finalize: () => {
                  patchState(store, { loading: null });
                  loadList();
                },
                error: (error) => {
                  toastService.error(error);
                },
              }),
            ),
          ),
        ),
      ),
    };
  }),
  withHooks({
    onInit: (store) => {
      effect(() => {
        store.hostId();
        patchState(store, { pruneResult: null }, removeAllEntities());
      });
      effect(() => {
        store.selectedId();
        patchState(store, { selectedInfo: null });
      });
    },
  }),
);
