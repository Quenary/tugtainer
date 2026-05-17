import { TestBed } from '@angular/core/testing';
import { signal, WritableSignal } from '@angular/core';
import { of, throwError } from 'rxjs';
import { ContainersStore, IContainerEntity } from './containers.store';
import { ContainersApiService } from './containers-api.service';
import { ToastService } from 'src/app/core/services/toast.service';
import { HostsStore, IHostEntity } from '../hosts/hosts.store';
import { TranslateService } from '@ngx-translate/core';
import {
  EContainerStatus,
  IContainerInfo,
  IContainerInspectResult,
} from './containers.interface';
import dayjs from 'dayjs';
import { EActionStatus } from '@shared/interfaces/progress.interface';

describe('ContainersStore', () => {
  let store: InstanceType<typeof ContainersStore>;

  let containersApiService: jasmine.SpyObj<ContainersApiService>;
  let toastService: jasmine.SpyObj<ToastService>;
  let translateService: jasmine.SpyObj<TranslateService>;
  let hostsStore: jasmine.SpyObj<InstanceType<typeof HostsStore>>;

  let hostSelectedIdSignal: WritableSignal<number | null>;
  let hostSelectedSignal: WritableSignal<IHostEntity>;
  let updateContainersListSignal: WritableSignal<Date | null>;

  const mockHost = {
    id: 1,
    name: 'Host 1',
  } as IHostEntity;

  const mockContainerItem = {
    id: 1,
    name: 'nginx',
    container_id: 'container-1',
    update_available: true,
    status: EContainerStatus.running,
  } as IContainerEntity;

  const mockContainerInspect = {
    Id: 'test-id',
    Created: dayjs().format(),
  } as IContainerInspectResult;

  const mockContainerInfo = {
    item: mockContainerItem,
    inspect: mockContainerInspect,
  } as IContainerInfo;

  beforeEach(() => {
    hostSelectedIdSignal = signal(1);

    hostSelectedSignal = signal(mockHost);

    updateContainersListSignal = signal<Date | null>(null);

    containersApiService = jasmine.createSpyObj<ContainersApiService>(
      'ContainersApiService',
      [
        'list',
        'get',
        'checkContainer',
        'updateContainer',
        'watchProgress',
        'patch',
        'controlContainer',
      ],
    );

    toastService = jasmine.createSpyObj<ToastService>('ToastService', [
      'error',
      'success',
    ]);

    translateService = jasmine.createSpyObj<TranslateService>(
      'TranslateService',
      ['instant'],
    );

    hostsStore = jasmine.createSpyObj<InstanceType<typeof HostsStore>>(
      'HostsStore',
      [],
      {
        selectedId: hostSelectedIdSignal,
        selected: hostSelectedSignal,
        updateContainersList: updateContainersListSignal,
      },
    );

    translateService.instant.and.callFake((v: string) => v);
    containersApiService.list.and.returnValue(of([mockContainerItem]));
    containersApiService.get.and.returnValue(of(mockContainerInfo));

    TestBed.configureTestingModule({
      providers: [
        ContainersStore,
        {
          provide: ContainersApiService,
          useValue: containersApiService,
        },
        {
          provide: ToastService,
          useValue: toastService,
        },
        {
          provide: TranslateService,
          useValue: translateService,
        },
        {
          provide: HostsStore,
          useValue: hostsStore,
        },
      ],
    });

    store = TestBed.inject(ContainersStore);
  });

  it('should initialize', () => {
    expect(store.loading()).toBeFalse();
    expect(store.selectedNameOrId()).toBeNull();
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

    describe('anyForUpdate', () => {
      it('should be true', () => {
        store.loadList();

        expect(store.anyForUpdate()).toBeTrue();
      });

      it('should be false', () => {
        containersApiService.list.and.returnValue(
          of([
            {
              ...mockContainerItem,
              update_available: false,
            },
          ]),
        );

        store.loadList();

        expect(store.anyForUpdate()).toBeFalse();
      });
    });

    describe('selected', () => {
      beforeEach(() => {
        store.loadList();
      });

      it('should select by name', () => {
        store.select('nginx');

        expect(store.selected()).toEqual(mockContainerItem);
      });

      it('should select by container_id', () => {
        store.select('container-1');

        expect(store.selected()).toEqual(mockContainerItem);
      });

      it('should return null if selected not found', () => {
        store.select('unknown');

        expect(store.selected()).toBeNull();
      });

      it('should return null if no selectedNameOrId', () => {
        store.select(null);

        expect(store.selected()).toBeNull();
      });
    });
  });

  describe('select', () => {
    it('should set selectedNameOrId', () => {
      store.select('nginx');

      expect(store.selectedNameOrId()).toBe('nginx');
    });

    it('should reset selectedInfo on selection change', () => {
      store.loadList();
      store.select('nginx');
      store.loadSelected();

      expect(store.selectedInfo()).toEqual(mockContainerInfo);

      store.select('another');
      TestBed.tick();

      expect(store.selectedInfo()).toBeNull();
    });
  });

  describe('loadList', () => {
    it('should load containers list', () => {
      store.loadList();

      expect(containersApiService.list).toHaveBeenCalledWith(1);
      expect(store.entities()).toEqual([mockContainerItem]);
    });

    it('should show error on load failure', () => {
      const error = new Error('Load failed');
      containersApiService.list.and.returnValue(throwError(() => error));

      store.loadList();

      expect(toastService.error).toHaveBeenCalledWith(error);
    });

    it('should not load if hostId is null', () => {
      hostSelectedIdSignal.set(null);

      store.loadList();

      expect(containersApiService.list).not.toHaveBeenCalled();
    });

    it('should clear entities on host change', () => {
      store.loadList();

      expect(store.entities().length).toBe(1);

      hostSelectedIdSignal.set(2);
      TestBed.tick();

      expect(store.entities()).toEqual([]);
    });
  });

  describe('loadSelected', () => {
    beforeEach(() => {
      store.loadList();
      store.select('nginx');
    });

    it('should load', () => {
      store.loadSelected();

      expect(containersApiService.get).toHaveBeenCalledWith(1, 'nginx');
      expect(store.selectedInfo()).toEqual(mockContainerInfo);
    });

    it('should show error on loadSelected failure', () => {
      const error = new Error('Inspect failed');
      containersApiService.get.and.returnValue(throwError(() => error));

      store.loadSelected();

      expect(toastService.error).toHaveBeenCalledWith(error);
    });

    it('should not load if hostId is null', () => {
      hostSelectedIdSignal.set(null);
      store.loadSelected();

      expect(containersApiService.get).not.toHaveBeenCalled();
    });

    it('should not load if selectedNameOrId is null', () => {
      store.select(null);
      store.loadSelected();

      expect(containersApiService.get).not.toHaveBeenCalled();
    });
  });

  describe('reloadEntity', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should reload entity', () => {
      store.reloadEntity({ id: 1 });

      expect(containersApiService.get).toHaveBeenCalledWith(1, 'nginx');
    });

    it('should update entity after reload', () => {
      containersApiService.get.and.returnValue(
        of({
          item: {
            ...mockContainerItem,
            status: EContainerStatus.exited,
          },
          inspect: mockContainerInspect,
        }),
      );

      store.reloadEntity({ id: 1 });

      expect(store.entityMap()[1].status).toBe(EContainerStatus.exited);
    });

    it('should show error on reload failure', () => {
      const error = new Error('Reload failed');
      containersApiService.get.and.returnValue(throwError(() => error));

      store.reloadEntity({ id: 1 });

      expect(toastService.error).toHaveBeenCalledWith(error);
    });

    it('should not reload if entity not found', () => {
      store.reloadEntity({ id: 999 });

      expect(containersApiService.get).not.toHaveBeenCalled();
    });
  });

  describe('patchContainer', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should patch container', () => {
      containersApiService.patch.and.returnValue(
        of({
          ...mockContainerItem,
          update_available: false,
          update_enabled: false,
        }),
      );

      store.patchContainer({
        id: 1,
        body: {
          update_enabled: false,
        },
      });

      expect(containersApiService.patch).toHaveBeenCalledWith(1, 'nginx', {
        update_enabled: false,
      });
      expect(store.entityMap()[1].update_available).toBeFalse();
      expect(store.entityMap()[1].update_enabled).toBeFalse();
    });

    it('should show error on patch failure', () => {
      const error = new Error('Patch failed');
      containersApiService.patch.and.returnValue(throwError(() => error));

      store.patchContainer({
        id: 1,
        body: {},
      });

      expect(toastService.error).toHaveBeenCalledWith(error);
    });
  });

  describe('controlContainer', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should control container', () => {
      const updated: IContainerEntity = {
        ...mockContainerItem,
        status: EContainerStatus.exited,
      };
      containersApiService.controlContainer.and.returnValue(
        of({
          item: updated,
          inspect: mockContainerInspect,
        }),
      );

      store.controlContainer({
        id: 1,
        command: 'stop',
      });

      expect(containersApiService.controlContainer).toHaveBeenCalledWith(
        1,
        'stop',
        'container-1',
      );
      expect(store.entityMap()[1].status).toBe(EContainerStatus.exited);
    });

    it('should show error on control failure', () => {
      const error = new Error('Control failed');
      containersApiService.controlContainer.and.returnValue(
        throwError(() => error),
      );

      store.controlContainer({
        id: 1,
        command: 'restart',
      });

      expect(toastService.error).toHaveBeenCalledWith(error);
    });
  });

  describe('checkContainer', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should check container', () => {
      containersApiService.checkContainer.and.returnValue(of('cache-id'));
      containersApiService.watchProgress.and.returnValue(
        of({
          status: EActionStatus.DONE,
        }),
      );

      store.checkContainer({ id: 1 });

      expect(containersApiService.checkContainer).toHaveBeenCalledWith(
        1,
        'nginx',
      );
      expect(containersApiService.watchProgress).toHaveBeenCalledWith(
        'cache-id',
      );
    });

    it('should show error on check failure', () => {
      const error = new Error('Check failed');
      containersApiService.checkContainer.and.returnValue(
        throwError(() => error),
      );

      store.checkContainer({ id: 1 });

      expect(toastService.error).toHaveBeenCalledWith(error);
    });
  });

  describe('updateContainer', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should update container', () => {
      containersApiService.updateContainer.and.returnValue(of('cache-id'));

      containersApiService.watchProgress.and.returnValue(
        of({
          status: EActionStatus.DONE,
        }),
      );

      store.updateContainer({ id: 1 });

      expect(containersApiService.updateContainer).toHaveBeenCalledWith(
        1,
        'nginx',
      );
      expect(containersApiService.watchProgress).toHaveBeenCalledWith(
        'cache-id',
      );
    });

    it('should show error on update failure', () => {
      const error = new Error('Update failed');
      containersApiService.updateContainer.and.returnValue(
        throwError(() => error),
      );

      store.updateContainer({ id: 1 });

      expect(toastService.error).toHaveBeenCalledWith(error);
    });
  });

  describe('updateContainersList effect', () => {
    it('should reload list on updateContainersList change', () => {
      updateContainersListSignal.set(new Date());
      TestBed.tick();

      expect(containersApiService.list).toHaveBeenCalledTimes(1);
    });

    it('should not reload if updateContainersList is null', () => {
      updateContainersListSignal.set(null);
      TestBed.tick();

      expect(containersApiService.list).not.toHaveBeenCalled();
    });
  });
});
