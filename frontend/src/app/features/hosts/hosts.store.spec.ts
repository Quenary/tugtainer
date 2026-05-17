import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { of, throwError } from 'rxjs';
import { HostsStore } from './hosts.store';
import { HostsApiService } from './hosts-api.service';
import { ToastService } from 'src/app/core/services/toast.service';
import { TranslateService } from '@ngx-translate/core';
import { ContainersApiService } from '../containers/containers-api.service';
import { PublicApiService } from '../public/public-api.service';
import { ImagesApiService } from '../images/images-api.service';
import { DialogService } from 'primeng/dynamicdialog';
import { ICreateHost, IHostInfo, IHostStatus } from './hosts.interface';
import { provideZonelessChangeDetection } from '@angular/core';
import { IActionProgress } from '@shared/interfaces/progress.interface';
import { IPruneImageRequestBodySchema } from '../images/images.interface';

describe('HostsStore', () => {
  let store: InstanceType<typeof HostsStore>;

  let hostsApiService: jasmine.SpyObj<HostsApiService>;
  let toastService: jasmine.SpyObj<ToastService>;
  let router: jasmine.SpyObj<Router>;
  let translateService: jasmine.SpyObj<TranslateService>;
  let containersApiService: jasmine.SpyObj<ContainersApiService>;
  let publicApiService: jasmine.SpyObj<PublicApiService>;
  let imagesApiService: jasmine.SpyObj<ImagesApiService>;
  let dialogService: jasmine.SpyObj<DialogService>;

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
    hostsApiService = jasmine.createSpyObj<HostsApiService>('HostsApiService', [
      'list',
      'create',
      'update',
      'delete',
      'status',
    ]);

    toastService = jasmine.createSpyObj<ToastService>('ToastService', [
      'success',
      'error',
    ]);

    router = jasmine.createSpyObj<Router>('Router', ['navigate']);

    translateService = jasmine.createSpyObj<TranslateService>(
      'TranslateService',
      ['instant'],
    );

    containersApiService = jasmine.createSpyObj<ContainersApiService>(
      'ContainersApiService',
      ['checkAll', 'updateAll', 'checkHost', 'updateHost', 'watchProgress'],
    );

    publicApiService = jasmine.createSpyObj<PublicApiService>(
      'PublicApiService',
      ['getSummary'],
    );

    imagesApiService = jasmine.createSpyObj<ImagesApiService>(
      'ImagesApiService',
      ['prune'],
    );

    dialogService = jasmine.createSpyObj<DialogService>('DialogService', [
      'open',
    ]);

    translateService.instant.and.callFake((v: string) => v);
    hostsApiService.list.and.returnValue(of([mockHost]));
    hostsApiService.status.and.returnValue(of(successStatus));
    publicApiService.getSummary.and.returnValue(of([]));

    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        HostsStore,
        {
          provide: HostsApiService,
          useValue: hostsApiService,
        },
        {
          provide: ToastService,
          useValue: toastService,
        },
        {
          provide: Router,
          useValue: router,
        },
        {
          provide: TranslateService,
          useValue: translateService,
        },
        {
          provide: ContainersApiService,
          useValue: containersApiService,
        },
        {
          provide: PublicApiService,
          useValue: publicApiService,
        },
        {
          provide: ImagesApiService,
          useValue: imagesApiService,
        },
        {
          provide: DialogService,
          useValue: dialogService,
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
      expect(store.anyForUpdate()).toBeTrue();
    });

    it('should return globalActionActive=false initially', () => {
      expect(store.globalActionActive()).toBeFalse();
    });
  });

  describe('loadList', () => {
    it('should load hosts list', () => {
      store.loadList();
      expect(hostsApiService.list).toHaveBeenCalled();
      expect(store.entities().length).toBe(1);
      expect(store.entities()[0].id).toBe(1);
    });

    it('should call toastService.error on error', () => {
      const error = new Error('Load failed');
      hostsApiService.list.and.returnValue(throwError(() => error));
      store.loadList();
      expect(toastService.error).toHaveBeenCalledWith(error);
    });

    it('should call loadStatusOf for enabled hosts', () => {
      store.loadList();
      expect(hostsApiService.status).toHaveBeenCalledWith(1);
    });
  });

  describe('create', () => {
    it('should create host', () => {
      hostsApiService.create.and.returnValue(of(mockHost));
      publicApiService.getSummary.and.returnValue(of([]));

      store.create({
        body: {
          id: 1,
          name: 'Host 1',
        } as IHostInfo,
      });

      expect(hostsApiService.create).toHaveBeenCalled();
      expect(store.entities().length).toBe(1);
      expect(router.navigate).toHaveBeenCalledWith(['/hosts/1'], {
        replaceUrl: true,
      });
    });

    it('should show error on create failure', () => {
      const error = new Error('Create failed');
      hostsApiService.create.and.returnValue(throwError(() => error));

      store.create({
        body: {} as ICreateHost,
      });

      expect(toastService.error).toHaveBeenCalledWith(error);
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
      hostsApiService.update.and.returnValue(of(updatedHost));

      store.update({
        id: 1,
        body: {} as ICreateHost,
      });

      expect(hostsApiService.update).toHaveBeenCalledWith(
        1,
        jasmine.any(Object),
      );
      expect(store.entityMap()[1].name).toBe('Updated Host');
    });

    it('should show error on update failure', () => {
      const error = new Error('Update failed');
      hostsApiService.update.and.returnValue(throwError(() => error));

      store.update({
        id: 1,
        body: {} as ICreateHost,
      });

      expect(toastService.error).toHaveBeenCalledWith(error);
    });
  });

  describe('delete', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should delete host', () => {
      hostsApiService.delete.and.returnValue(of({ detail: '' }));

      store.delete({ id: 1 });

      expect(hostsApiService.delete).toHaveBeenCalledWith(1);
      expect(store.entities().length).toBe(0);
      expect(router.navigate).toHaveBeenCalledWith(['/hosts'], {
        replaceUrl: true,
      });
      expect(toastService.success).toHaveBeenCalled();
    });

    it('should show error on delete failure', () => {
      const error = new Error('Delete failed');
      hostsApiService.delete.and.returnValue(throwError(() => error));

      store.delete({ id: 1 });

      expect(toastService.error).toHaveBeenCalledWith(error);
    });
  });

  describe('loadStatusOf', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should load host status', () => {
      store.loadStatusOf({ hostId: 1 });

      expect(hostsApiService.status).toHaveBeenCalledWith(1);
      expect(store.entityMap()[1].status).toEqual(successStatus);
    });

    it('should set failed status on error', () => {
      hostsApiService.status.and.returnValue(
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
      containersApiService.checkAll.and.returnValue(of('cache-id'));
      containersApiService.watchProgress.and.returnValue(
        of({
          status: 'DONE',
          result: {},
        } as IActionProgress),
      );

      store.checkAll();

      expect(containersApiService.checkAll).toHaveBeenCalled();
      expect(containersApiService.watchProgress).toHaveBeenCalledWith(
        'cache-id',
      );
    });

    it('should show error on checkAll failure', () => {
      const error = new Error('Check failed');
      containersApiService.checkAll.and.returnValue(throwError(() => error));

      store.checkAll();

      expect(toastService.error).toHaveBeenCalledWith(error);
    });
  });

  describe('checkHost', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should check host', () => {
      containersApiService.checkHost.and.returnValue(of('cache-id'));
      containersApiService.watchProgress.and.returnValue(
        of({
          status: 'DONE',
          result: {},
        } as IActionProgress),
      );

      store.checkHost({ id: 1 });

      expect(containersApiService.checkHost).toHaveBeenCalledWith(1);
    });
  });

  describe('pruneHost', () => {
    beforeEach(() => {
      store.loadList();
    });

    it('should prune host images', () => {
      imagesApiService.prune.and.returnValue(of('Pruned successfully'));
      store.pruneHost({
        id: 1,
        body: {} as IPruneImageRequestBodySchema,
      });

      expect(imagesApiService.prune).toHaveBeenCalledWith(
        1,
        jasmine.any(Object),
      );
      expect(store.entityMap()[1].pruneResult).toBe('Pruned successfully');
      expect(dialogService.open).toHaveBeenCalled();
    });

    it('should show error on prune failure', () => {
      const error = new Error('Prune failed');
      imagesApiService.prune.and.returnValue(throwError(() => error));

      store.pruneHost({
        id: 1,
        body: {} as IPruneImageRequestBodySchema,
      });

      expect(toastService.error).toHaveBeenCalledWith(error);
    });
  });

  describe('openActionResultDialog', () => {
    it('should open dialog', () => {
      store.openActionResultDialog([], null);
      expect(dialogService.open).toHaveBeenCalled();
    });
  });
});
