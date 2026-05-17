import { TestBed } from '@angular/core/testing';
import { signal, WritableSignal } from '@angular/core';
import { of, throwError } from 'rxjs';
import { ImagesStore } from './images.store';
import { ImagesApiService } from './images-api.service';
import { ToastService } from 'src/app/core/services/toast.service';
import { HostsStore, IHostEntity } from '../hosts/hosts.store';
import { IImage, IImageInspectResult } from './images.interface';

describe('ImagesStore', () => {
  let store: InstanceType<typeof ImagesStore>;

  let imagesApiService: jasmine.SpyObj<ImagesApiService>;
  let toastService: jasmine.SpyObj<ToastService>;
  let hostsStore: jasmine.SpyObj<InstanceType<typeof HostsStore>>;

  let selectedIdSignal: WritableSignal<number | null>;
  let selectedSignal: WritableSignal<IHostEntity>;
  let updateImagesListSignal: WritableSignal<Date | null>;

  const mockHost = {
    id: 1,
    name: 'Host 1',
  } as IHostEntity;

  const mockImage = {
    id: 'img-1',
    tags: ['nginx:latest'],
    size: 12345,
  } as IImage;

  const mockInspectResult = {
    Id: 'img-1',
    RepoTags: ['nginx:latest'],
  } as IImageInspectResult;

  beforeEach(() => {
    selectedIdSignal = signal(1);
    selectedSignal = signal(mockHost);
    updateImagesListSignal = signal<Date | null>(null);

    imagesApiService = jasmine.createSpyObj<ImagesApiService>(
      'ImagesApiService',
      ['list', 'inspect'],
    );

    toastService = jasmine.createSpyObj<ToastService>('ToastService', [
      'error',
    ]);

    hostsStore = jasmine.createSpyObj<InstanceType<typeof HostsStore>>(
      'HostsStore',
      [],
      {
        selectedId: selectedIdSignal,
        selected: selectedSignal,
        updateImagesList: updateImagesListSignal,
      },
    );

    imagesApiService.list.and.returnValue(of([mockImage]));
    imagesApiService.inspect.and.returnValue(of(mockInspectResult));

    TestBed.configureTestingModule({
      providers: [
        ImagesStore,
        {
          provide: ImagesApiService,
          useValue: imagesApiService,
        },
        {
          provide: ToastService,
          useValue: toastService,
        },
        {
          provide: HostsStore,
          useValue: hostsStore,
        },
      ],
    });

    store = TestBed.inject(ImagesStore);
  });

  it('should initialize', () => {
    expect(store.loading()).toBeFalse();
    expect(store.selectedId()).toBeNull();
    expect(store.selectedInfo()).toBeNull();
    expect(store.entities()).toEqual([]);
    expect(store.ids()).toEqual([]);
  });

  describe('computed', () => {
    it('should return hostId', () => {
      expect(store.hostId()).toBe(1);
    });

    it('should return host', () => {
      expect(store.host()).toEqual(mockHost);
    });

    describe('selected', () => {
      beforeEach(() => {
        store.loadList();
      });

      it('should return image entity', () => {
        store.select('img-1');
        expect(store.selected()).toEqual(mockImage);
      });

      it('should return null if entity not found', () => {
        store.select('unknown');
        expect(store.selected()).toBeNull();
      });

      it('should return null if no selectedId', () => {
        store.select(null);
        expect(store.selected()).toBeNull();
      });
    });
  });

  describe('select', () => {
    it('should set selectedId', () => {
      store.select('img-1');

      expect(store.selectedId()).toBe('img-1');
    });

    it('should reset selectedInfo after selectedId change', () => {
      store.loadList();
      store.select('img-1');
      store.loadSelected();

      expect(store.selectedInfo()).toEqual(mockInspectResult);

      store.select('img-2');
      TestBed.tick();

      expect(store.selectedInfo()).toBeNull();
    });
  });

  describe('loadList', () => {
    it('should load', () => {
      store.loadList();

      expect(imagesApiService.list).toHaveBeenCalledWith(1);
      expect(store.entities().length).toBe(1);
      expect(store.entities()[0].id).toBe('img-1');
    });

    it('should show error on load failure', () => {
      const error = new Error('Load failed');
      imagesApiService.list.and.returnValue(throwError(() => error));

      store.loadList();

      expect(toastService.error).toHaveBeenCalledWith(error);
    });

    it('should not load if hostId is null', () => {
      selectedIdSignal.set(null);
      store.loadList();

      expect(imagesApiService.list).not.toHaveBeenCalled();
    });

    it('should clear entities when host changes', () => {
      store.loadList();

      expect(store.entities().length).toBe(1);

      selectedIdSignal.set(2);
      TestBed.tick();

      expect(store.entities().length).toBe(0);
    });
  });

  describe('loadSelected', () => {
    beforeEach(() => {
      store.loadList();
      store.select('img-1');
    });

    it('should load', () => {
      imagesApiService.inspect.and.returnValue(of(mockInspectResult));

      store.loadSelected();

      expect(imagesApiService.inspect).toHaveBeenCalledWith(1, 'img-1');
      expect(store.selectedInfo()).toEqual(mockInspectResult);
    });

    it('should show error on inspect failure', () => {
      const error = new Error('Inspect failed');
      imagesApiService.inspect.and.returnValue(throwError(() => error));

      store.loadSelected();

      expect(toastService.error).toHaveBeenCalledWith(error);
    });

    it('should not call inspect if selectedId is null', () => {
      selectedIdSignal.set(1);
      store.select(null);
      store.loadSelected();

      expect(imagesApiService.inspect).not.toHaveBeenCalled();
    });

    it('should not call inspect if hostId is null', () => {
      store.select('img-1');
      selectedIdSignal.set(null);
      store.loadSelected();

      expect(imagesApiService.inspect).not.toHaveBeenCalled();
    });
  });

  describe('updateImagesList effect', () => {
    it('should reload list when updateImagesList changes', () => {
      updateImagesListSignal.set(new Date());
      TestBed.tick();
      expect(imagesApiService.list).toHaveBeenCalledWith(1);
    });

    it('should not reload if updateImagesList is null', () => {
      updateImagesListSignal.set(null);
      TestBed.tick();
      expect(imagesApiService.list).not.toHaveBeenCalled();
    });
  });
});
