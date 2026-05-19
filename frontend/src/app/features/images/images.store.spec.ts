import { TestBed } from '@angular/core/testing';
import { signal, WritableSignal } from '@angular/core';
import { of, throwError } from 'rxjs';
import { ImagesStore } from './images.store';
import { ImagesApiService } from './images-api.service';
import { ToastService } from 'src/app/core/services/toast.service';
import { HostsStore, IHostEntity } from '../hosts/hosts.store';
import { IImage, IImageInspectResult } from './images.interface';
import { Mocked } from 'vitest';
import { getToastServiceMock } from '@testing/mocks/toast-service.mock';
import { getImagesApiServiceMock } from '@testing/mocks/images-api.service.mock';

describe('ImagesStore', () => {
  let store: InstanceType<typeof ImagesStore>;

  let imagesApiServiceMock: Mocked<ImagesApiService>;
  let toastServiceMock: Mocked<ToastService>;
  let hostsStoreMock: Partial<InstanceType<typeof HostsStore>>;

  let hostSelectedIdSignal: WritableSignal<number | null>;
  let hostSelectedSignal: WritableSignal<IHostEntity>;
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
    imagesApiServiceMock = getImagesApiServiceMock();
    imagesApiServiceMock.list.mockReturnValue(of([mockImage]));
    imagesApiServiceMock.inspect.mockReturnValue(of(mockInspectResult));

    toastServiceMock = getToastServiceMock();

    hostSelectedIdSignal = signal(1);
    hostSelectedSignal = signal(mockHost);
    updateImagesListSignal = signal<Date | null>(null);
    hostsStoreMock = {
      selectedId: hostSelectedIdSignal,
      selected: hostSelectedSignal,
      updateImagesList: updateImagesListSignal,
    };

    TestBed.configureTestingModule({
      providers: [
        ImagesStore,
        {
          provide: ImagesApiService,
          useValue: imagesApiServiceMock,
        },
        {
          provide: ToastService,
          useValue: toastServiceMock,
        },
        {
          provide: HostsStore,
          useValue: hostsStoreMock,
        },
      ],
    });

    store = TestBed.inject(ImagesStore);
  });

  it('should initialize', () => {
    expect(store.loading()).toBe(false);
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

      expect(imagesApiServiceMock.list).toHaveBeenCalledWith(1);
      expect(store.entities().length).toBe(1);
      expect(store.entities()[0].id).toBe('img-1');
    });

    it('should show error on load failure', () => {
      const error = new Error('Load failed');
      imagesApiServiceMock.list.mockReturnValue(throwError(() => error));

      store.loadList();

      expect(toastServiceMock.error).toHaveBeenCalledWith(error);
    });

    it('should not load if hostId is null', () => {
      hostSelectedIdSignal.set(null);
      store.loadList();

      expect(imagesApiServiceMock.list).not.toHaveBeenCalled();
    });

    it('should clear entities when host changes', () => {
      store.loadList();

      expect(store.entities().length).toBe(1);

      hostSelectedIdSignal.set(2);
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
      imagesApiServiceMock.inspect.mockReturnValue(of(mockInspectResult));

      store.loadSelected();

      expect(imagesApiServiceMock.inspect).toHaveBeenCalledWith(1, 'img-1');
      expect(store.selectedInfo()).toEqual(mockInspectResult);
    });

    it('should show error on inspect failure', () => {
      const error = new Error('Inspect failed');
      imagesApiServiceMock.inspect.mockReturnValue(throwError(() => error));

      store.loadSelected();

      expect(toastServiceMock.error).toHaveBeenCalledWith(error);
    });

    it('should not call inspect if selectedId is null', () => {
      hostSelectedIdSignal.set(1);
      store.select(null);
      store.loadSelected();

      expect(imagesApiServiceMock.inspect).not.toHaveBeenCalled();
    });

    it('should not call inspect if hostId is null', () => {
      store.select('img-1');
      hostSelectedIdSignal.set(null);
      store.loadSelected();

      expect(imagesApiServiceMock.inspect).not.toHaveBeenCalled();
    });
  });

  describe('updateImagesList effect', () => {
    it('should reload list when updateImagesList changes', () => {
      updateImagesListSignal.set(new Date());
      TestBed.tick();
      expect(imagesApiServiceMock.list).toHaveBeenCalledWith(1);
    });

    it('should not reload if updateImagesList is null', () => {
      updateImagesListSignal.set(null);
      TestBed.tick();
      expect(imagesApiServiceMock.list).not.toHaveBeenCalled();
    });
  });
});
