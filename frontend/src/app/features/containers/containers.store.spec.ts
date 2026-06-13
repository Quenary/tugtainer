import { TestBed } from '@angular/core/testing';
import { signal, WritableSignal } from '@angular/core';
import { of, throwError } from 'rxjs';
import { ContainersStore, IContainerEntity } from './containers.store';
import { ContainersApiService } from './containers-api.service';
import { ToastService } from 'src/app/core/services/toast.service';
import { HostsStore, IHostEntity } from '../hosts/hosts.store';
import { provideTranslateService } from '@ngx-translate/core';
import {
  EContainerStatus,
  IContainerInfo,
  IContainerInspectResult,
} from './containers.interface';
import dayjs from 'dayjs';
import { EActionStatus } from '@shared/interfaces/progress.interface';
import { Mocked } from 'vitest';
import { getToastServiceMock } from '@testing/mocks/toast-service.mock';
import { getContainersApiServiceMock } from '@testing/mocks/containers-api.service.mock';

describe('ContainersStore', () => {
  let store: InstanceType<typeof ContainersStore>;

  let containersApiServiceMock: Mocked<ContainersApiService>;
  let toastServiceMock: Mocked<ToastService>;
  let hostsStoreMock: Partial<InstanceType<typeof HostsStore>>;

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
    containersApiServiceMock = getContainersApiServiceMock();
    containersApiServiceMock.list.mockReturnValue(of([mockContainerItem]));
    containersApiServiceMock.get.mockReturnValue(of(mockContainerInfo));

    toastServiceMock = getToastServiceMock();

    hostSelectedIdSignal = signal(1);
    hostSelectedSignal = signal(mockHost);
    updateContainersListSignal = signal<Date | null>(null);
    hostsStoreMock = {
      selectedId: hostSelectedIdSignal,
      selected: hostSelectedSignal,
      updateContainersList: updateContainersListSignal,
    };

    TestBed.configureTestingModule({
      providers: [
        ContainersStore,
        {
          provide: ContainersApiService,
          useValue: containersApiServiceMock,
        },
        {
          provide: ToastService,
          useValue: toastServiceMock,
        },
        provideTranslateService(),
        {
          provide: HostsStore,
          useValue: hostsStoreMock,
        },
      ],
    });

    store = TestBed.inject(ContainersStore);
  });

  it('should initialize', () => {
    expect(store.loading()).toBe(false);
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

        expect(store.anyForUpdate()).toBe(true);
      });

      it('should be false', () => {
        containersApiServiceMock.list.mockReturnValue(
          of([
            {
              ...mockContainerItem,
              update_available: false,
            },
          ]),
        );

        store.loadList();

        expect(store.anyForUpdate()).toBe(false);
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

      expect(containersApiServiceMock.list).toHaveBeenCalledWith(1);
      expect(store.entities()).toEqual([mockContainerItem]);
    });

    it('should show error on load failure', () => {
      const error = new Error('Load failed');
      containersApiServiceMock.list.mockReturnValue(throwError(() => error));

      store.loadList();

      expect(toastServiceMock.error).toHaveBeenCalledWith(error);
    });

    it('should not load if hostId is null', () => {
      hostSelectedIdSignal.set(null);

      store.loadList();

      expect(containersApiServiceMock.list).not.toHaveBeenCalled();
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

      expect(containersApiServiceMock.get).toHaveBeenCalledWith(1, 'nginx');
      expect(store.selectedInfo()).toEqual(mockContainerInfo);
    });

    it('should show error on loadSelected failure', () => {
      const error = new Error('Inspect failed');
      containersApiServiceMock.get.mockReturnValue(throwError(() => error));

      store.loadSelected();

      expect(toastServiceMock.error).toHaveBeenCalledWith(error);
    });

    it('should not load if hostId is null', () => {
      hostSelectedIdSignal.set(null);
      store.loadSelected();

      expect(containersApiServiceMock.get).not.toHaveBeenCalled();
    });

    it('should not load if selectedNameOrId is null', () => {
      store.select(null);
      store.loadSelected();

      expect(containersApiServiceMock.get).not.toHaveBeenCalled();
    });
  });

  describe('reloadEntity', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should reload entity', () => {
      store.reloadEntity({ containerName: 'nginx' });

      expect(containersApiServiceMock.get).toHaveBeenCalledWith(1, 'nginx');
    });

    it('should update entity after reload', () => {
      containersApiServiceMock.get.mockReturnValue(
        of({
          item: {
            ...mockContainerItem,
            status: EContainerStatus.exited,
          },
          inspect: mockContainerInspect,
        }),
      );

      store.reloadEntity({ containerName: 'nginx' });

      expect(store.entityMap()['nginx'].status).toBe(EContainerStatus.exited);
    });

    it('should show error on reload failure', () => {
      const error = new Error('Reload failed');
      containersApiServiceMock.get.mockReturnValue(throwError(() => error));

      store.reloadEntity({ containerName: 'nginx' });

      expect(toastServiceMock.error).toHaveBeenCalledWith(error);
    });
  });

  describe('patchContainer', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should patch container', () => {
      containersApiServiceMock.patch.mockReturnValue(
        of({
          ...mockContainerItem,
          update_available: false,
          update_enabled: false,
        }),
      );

      store.patchContainer({
        containerName: 'nginx',
        body: {
          update_enabled: false,
        },
      });

      expect(containersApiServiceMock.patch).toHaveBeenCalledWith(1, 'nginx', {
        update_enabled: false,
      });
      expect(store.entityMap()['nginx'].update_available).toBe(false);
      expect(store.entityMap()['nginx'].update_enabled).toBe(false);
    });

    it('should show error on patch failure', () => {
      const error = new Error('Patch failed');
      containersApiServiceMock.patch.mockReturnValue(throwError(() => error));

      store.patchContainer({
        containerName: 'nginx',
        body: {},
      });

      expect(toastServiceMock.error).toHaveBeenCalledWith(error);
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
      containersApiServiceMock.controlContainer.mockReturnValue(
        of({
          item: updated,
          inspect: mockContainerInspect,
        }),
      );

      store.controlContainer({
        containerName: 'nginx',
        command: 'stop',
      });

      expect(containersApiServiceMock.controlContainer).toHaveBeenCalledWith(
        1,
        'stop',
        'nginx',
      );
      expect(store.entityMap()['nginx'].status).toBe(EContainerStatus.exited);
    });

    it('should show error on control failure', () => {
      const error = new Error('Control failed');
      containersApiServiceMock.controlContainer.mockReturnValue(
        throwError(() => error),
      );

      store.controlContainer({
        containerName: 'nginx',
        command: 'restart',
      });

      expect(toastServiceMock.error).toHaveBeenCalledWith(error);
    });
  });

  describe('checkContainer', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should check container', () => {
      containersApiServiceMock.checkContainer.mockReturnValue(of('cache-id'));
      containersApiServiceMock.watchProgress.mockReturnValue(
        of({
          status: EActionStatus.DONE,
        }),
      );

      store.checkContainer({ containerName: 'nginx' });

      expect(containersApiServiceMock.checkContainer).toHaveBeenCalledWith(
        1,
        'nginx',
      );
      expect(containersApiServiceMock.watchProgress).toHaveBeenCalledWith(
        'cache-id',
      );
    });

    it('should show error on check failure', () => {
      const error = new Error('Check failed');
      containersApiServiceMock.checkContainer.mockReturnValue(
        throwError(() => error),
      );

      store.checkContainer({ containerName: 'nginx' });

      expect(toastServiceMock.error).toHaveBeenCalledWith(error);
    });
  });

  describe('updateContainer', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should update container', () => {
      containersApiServiceMock.updateContainer.mockReturnValue(of('cache-id'));

      containersApiServiceMock.watchProgress.mockReturnValue(
        of({
          status: EActionStatus.DONE,
        }),
      );

      store.updateContainer({ containerName: 'nginx' });

      expect(containersApiServiceMock.updateContainer).toHaveBeenCalledWith(
        1,
        'nginx',
      );
      expect(containersApiServiceMock.watchProgress).toHaveBeenCalledWith(
        'cache-id',
      );
    });

    it('should show error on update failure', () => {
      const error = new Error('Update failed');
      containersApiServiceMock.updateContainer.mockReturnValue(
        throwError(() => error),
      );

      store.updateContainer({ containerName: 'nginx' });

      expect(toastServiceMock.error).toHaveBeenCalledWith(error);
    });
  });

  describe('updateContainersList effect', () => {
    it('should reload list on updateContainersList change', () => {
      updateContainersListSignal.set(new Date());
      TestBed.tick();

      expect(containersApiServiceMock.list).toHaveBeenCalledTimes(1);
    });

    it('should not reload if updateContainersList is null', () => {
      updateContainersListSignal.set(null);
      TestBed.tick();

      expect(containersApiServiceMock.list).not.toHaveBeenCalled();
    });
  });
});
