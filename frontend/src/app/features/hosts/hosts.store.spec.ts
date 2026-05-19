import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { HostsStore } from './hosts.store';
import { HostsApiService } from './hosts-api.service';
import { ToastService } from 'src/app/core/services/toast.service';
import { provideTranslateService } from '@ngx-translate/core';
import { ContainersApiService } from '../containers/containers-api.service';
import { PublicApiService } from '../public/public-api.service';
import { ImagesApiService } from '../images/images-api.service';
import { DialogService } from 'primeng/dynamicdialog';
import { ICreateHost, IHostInfo, IHostStatus } from './hosts.interface';
import { provideZonelessChangeDetection } from '@angular/core';
import { IActionProgress } from '@shared/interfaces/progress.interface';
import { IPruneImageRequestBodySchema } from '../images/images.interface';
import { Mocked } from 'vitest';
import { getToastServiceMock } from '@testing/mocks/toast-service.mock';
import { getContainersApiServiceMock } from '@testing/mocks/containers-api.service.mock';
import { getImagesApiServiceMock } from '@testing/mocks/images-api.service.mock';
import { getPublicApiServiceMock } from '@testing/mocks/public-api.service.mock';

describe('HostsStore', () => {
  let store: InstanceType<typeof HostsStore>;

  let hostsApiServiceMock: Partial<Mocked<HostsApiService>>;
  let toastServiceMock: Mocked<ToastService>;
  let routerMock: Partial<Mocked<Router>>;
  let containersApiServiceMock: Mocked<ContainersApiService>;
  let publicApiServiceMock: Mocked<PublicApiService>;
  let imagesApiServiceMock: Mocked<ImagesApiService>;
  let dialogServiceMock: Partial<Mocked<DialogService>>;

  const mockHost = {
    id: 1,
    name: 'Host 1',
    enabled: true,
    available_updates_count: 2,
  } as IHostInfo;

  const successStatus: IHostStatus = {
    id: 1,
    ok: true,
    err: null,
  };

  beforeEach(() => {
    hostsApiServiceMock = {
      list: vi.fn().mockReturnValue(of([mockHost])),
      create: vi.fn(),
      update: vi.fn(),
      delete: vi.fn(),
      status: vi.fn().mockReturnValue(of(successStatus)),
    };

    toastServiceMock = getToastServiceMock();

    routerMock = {
      navigate: vi.fn(),
    };

    containersApiServiceMock = getContainersApiServiceMock();

    publicApiServiceMock = getPublicApiServiceMock();
    publicApiServiceMock.getSummary.mockReturnValue(of([]));

    imagesApiServiceMock = getImagesApiServiceMock();

    dialogServiceMock = {
      open: vi.fn() as Mocked<DialogService>['open'],
    };

    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        HostsStore,
        {
          provide: HostsApiService,
          useValue: hostsApiServiceMock,
        },
        {
          provide: ToastService,
          useValue: toastServiceMock,
        },
        {
          provide: Router,
          useValue: routerMock,
        },
        provideTranslateService(),
        {
          provide: ContainersApiService,
          useValue: containersApiServiceMock,
        },
        {
          provide: PublicApiService,
          useValue: publicApiServiceMock,
        },
        {
          provide: ImagesApiService,
          useValue: imagesApiServiceMock,
        },
        {
          provide: DialogService,
          useValue: dialogServiceMock,
        },
      ],
    });

    store = TestBed.inject(HostsStore);
  });

  describe('computed', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should return selected entity', () => {
      store.select(1);
      expect(store.selected().id).toBe(1);
    });

    it('should return anyForUpdate=true', () => {
      expect(store.anyForUpdate()).toBe(true);
    });

    it('should return globalActionActive=false initially', () => {
      expect(store.globalActionActive()).toBe(false);
    });
  });

  describe('loadList', () => {
    it('should load hosts list', () => {
      store.loadList();
      expect(hostsApiServiceMock.list).toHaveBeenCalled();
      expect(store.entities().length).toBe(1);
      expect(store.entities()[0].id).toBe(1);
    });

    it('should call toastService.error on error', () => {
      const error = new Error('Load failed');
      hostsApiServiceMock.list.mockReturnValue(throwError(() => error));
      store.loadList();
      expect(toastServiceMock.error).toHaveBeenCalledWith(error);
    });

    it('should call loadStatusOf for enabled hosts', () => {
      store.loadList();
      expect(hostsApiServiceMock.status).toHaveBeenCalledWith(1);
    });
  });

  describe('create', () => {
    it('should create host', () => {
      hostsApiServiceMock.create.mockReturnValue(of(mockHost));
      publicApiServiceMock.getSummary.mockReturnValue(of([]));

      store.create({
        body: {
          id: 1,
          name: 'Host 1',
        } as IHostInfo,
      });

      expect(hostsApiServiceMock.create).toHaveBeenCalled();
      expect(store.entities().length).toBe(1);
      expect(routerMock.navigate).toHaveBeenCalledWith(['/hosts/1'], {
        replaceUrl: true,
      });
    });

    it('should show error on create failure', () => {
      const error = new Error('Create failed');
      hostsApiServiceMock.create.mockReturnValue(throwError(() => error));

      store.create({
        body: {} as ICreateHost,
      });

      expect(toastServiceMock.error).toHaveBeenCalledWith(error);
    });
  });

  describe('update', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should update host', () => {
      const updatedHost = {
        ...mockHost,
        name: 'Updated Host',
      };
      hostsApiServiceMock.update.mockReturnValue(of(updatedHost));

      store.update({
        id: 1,
        body: {} as ICreateHost,
      });

      expect(hostsApiServiceMock.update).toHaveBeenCalledWith(
        1,
        expect.any(Object),
      );
      expect(store.entityMap()[1].name).toBe('Updated Host');
    });

    it('should show error on update failure', () => {
      const error = new Error('Update failed');
      hostsApiServiceMock.update.mockReturnValue(throwError(() => error));

      store.update({
        id: 1,
        body: {} as ICreateHost,
      });

      expect(toastServiceMock.error).toHaveBeenCalledWith(error);
    });
  });

  describe('delete', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should delete host', () => {
      hostsApiServiceMock.delete.mockReturnValue(of({ detail: '' }));

      store.delete({ id: 1 });

      expect(hostsApiServiceMock.delete).toHaveBeenCalledWith(1);
      expect(store.entities().length).toBe(0);
      expect(routerMock.navigate).toHaveBeenCalledWith(['/hosts'], {
        replaceUrl: true,
      });
      expect(toastServiceMock.success).toHaveBeenCalled();
    });

    it('should show error on delete failure', () => {
      const error = new Error('Delete failed');
      hostsApiServiceMock.delete.mockReturnValue(throwError(() => error));

      store.delete({ id: 1 });

      expect(toastServiceMock.error).toHaveBeenCalledWith(error);
    });
  });

  describe('loadStatusOf', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should load host status', () => {
      store.loadStatusOf({ hostId: 1 });

      expect(hostsApiServiceMock.status).toHaveBeenCalledWith(1);
      expect(store.entityMap()[1].status).toEqual(successStatus);
    });

    it('should set failed status on error', () => {
      hostsApiServiceMock.status.mockReturnValue(
        throwError(() => ({
          message: 'Connection failed',
        })),
      );

      store.loadStatusOf({ hostId: 1 });

      expect(store.entityMap()[1].status).toEqual({
        id: 1,
        ok: false,
        err: 'Connection failed',
      });
    });
  });

  describe('checkAll', () => {
    it('should check all hosts', () => {
      containersApiServiceMock.checkAll.mockReturnValue(of('cache-id'));
      containersApiServiceMock.watchProgress.mockReturnValue(
        of({
          status: 'DONE',
          result: {},
        } as IActionProgress),
      );

      store.checkAll();

      expect(containersApiServiceMock.checkAll).toHaveBeenCalled();
      expect(containersApiServiceMock.watchProgress).toHaveBeenCalledWith(
        'cache-id',
      );
    });

    it('should show error on checkAll failure', () => {
      const error = new Error('Check failed');
      containersApiServiceMock.checkAll.mockReturnValue(
        throwError(() => error),
      );

      store.checkAll();

      expect(toastServiceMock.error).toHaveBeenCalledWith(error);
    });
  });

  describe('checkHost', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should check host', () => {
      containersApiServiceMock.checkHost.mockReturnValue(of('cache-id'));
      containersApiServiceMock.watchProgress.mockReturnValue(
        of({
          status: 'DONE',
          result: {},
        } as IActionProgress),
      );

      store.checkHost({ id: 1 });

      expect(containersApiServiceMock.checkHost).toHaveBeenCalledWith(1);
    });
  });

  describe('pruneHost', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should prune host images', () => {
      imagesApiServiceMock.prune.mockReturnValue(of('Pruned successfully'));
      store.pruneHost({
        id: 1,
        body: {} as IPruneImageRequestBodySchema,
      });

      expect(imagesApiServiceMock.prune).toHaveBeenCalledWith(
        1,
        expect.any(Object),
      );
      expect(store.entityMap()[1].pruneResult).toBe('Pruned successfully');
      expect(dialogServiceMock.open).toHaveBeenCalled();
    });

    it('should show error on prune failure', () => {
      const error = new Error('Prune failed');
      imagesApiServiceMock.prune.mockReturnValue(throwError(() => error));

      store.pruneHost({
        id: 1,
        body: {} as IPruneImageRequestBodySchema,
      });

      expect(toastServiceMock.error).toHaveBeenCalledWith(error);
    });
  });

  describe('openActionResultDialog', () => {
    it('should open dialog', () => {
      store.openActionResultDialog([], null);
      expect(dialogServiceMock.open).toHaveBeenCalled();
    });
  });
});
