import { signal, WritableSignal } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideTranslateService } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';
import { ToastService } from 'src/app/core/services/toast.service';
import { getToastServiceMock } from '@testing/mocks/toast-service.mock';
import { EJobStatus } from '@shared/interfaces/jobs.interface';
import { HostsStore, IHostEntity } from '../../hosts/hosts.store';
import { ServicesApiService } from '../services-api.service';
import { IServiceEntity, ServicesStore } from '../services.store';
import { ServicesTableComponent } from './services-table.component';

const service = (
  partial: Partial<IServiceEntity> & Pick<IServiceEntity, 'name'>,
): IServiceEntity =>
  ({
    id: partial.name,
    image: `${partial.name}:latest`,
    mode: 'replicated',
    replicas_running: 1,
    replicas_desired: 1,
    check_enabled: true,
    update_enabled: true,
    update_available: false,
    available_version: null,
    available_created: null,
    checked_at: null,
    updated_at: null,
    update_status_state: null,
    update_status_message: null,
    labels: {},
    ...partial,
  }) as IServiceEntity;

describe('ServicesTableComponent', () => {
  let fixture: ComponentFixture<ServicesTableComponent>;
  let component: ServicesTableComponent;
  let entities: WritableSignal<IServiceEntity[]>;
  let selectedId: WritableSignal<number | null>;
  let selectedHost: WritableSignal<IHostEntity | null>;
  let servicesStore: {
    entities: WritableSignal<IServiceEntity[]>;
    loadList: ReturnType<typeof vi.fn>;
    checkServices: ReturnType<typeof vi.fn>;
    updateServices: ReturnType<typeof vi.fn>;
  };
  let logs: ReturnType<typeof vi.fn>;
  let toastService: ReturnType<typeof getToastServiceMock>;

  const pending = service({ name: 'api', update_available: true });
  const current = service({ name: 'worker' });

  beforeEach(async () => {
    entities = signal([pending, current]);
    selectedId = signal(7);
    selectedHost = signal(null);
    servicesStore = {
      entities,
      loadList: vi.fn(),
      checkServices: vi.fn(),
      updateServices: vi.fn(),
    };
    logs = vi.fn().mockReturnValue(of('line'));
    toastService = getToastServiceMock();

    await TestBed.configureTestingModule({
      imports: [ServicesTableComponent],
      providers: [
        provideTranslateService(),
        { provide: ServicesStore, useValue: servicesStore },
        {
          provide: HostsStore,
          useValue: { selectedId, selected: selectedHost },
        },
        { provide: ServicesApiService, useValue: { logs } },
        { provide: ToastService, useValue: toastService },
      ],
    })
      .overrideComponent(ServicesTableComponent, {
        set: { template: '' },
      })
      .compileComponents();

    fixture = TestBed.createComponent(ServicesTableComponent);
    component = fixture.componentInstance;
  });

  it('loads the list on init', () => {
    expect(servicesStore.loadList).toHaveBeenCalledTimes(1);
  });

  describe('filteredList', () => {
    it('includes every service', () => {
      expect(component['filteredList']().map((item) => item.name)).toEqual([
        'api',
        'worker',
      ]);
    });

    it('keeps services that have an update', () => {
      component['onlyAvailable'].set(true);

      expect(component['filteredList']().map((item) => item.name)).toEqual([
        'api',
      ]);
    });
  });

  describe('selection', () => {
    it('keeps services that have an update', () => {
      component['selected'].set([pending, current]);

      expect(component['updatableSelected']().map((item) => item.name)).toEqual(
        ['api'],
      );
    });

    it('checks every selected service and clears the selection', () => {
      component['selected'].set([pending, current]);

      component['onCheckSelected']();

      expect(servicesStore.checkServices).toHaveBeenCalledWith({
        names: ['api', 'worker'],
      });
      expect(component['selected']()).toEqual([]);
    });

    it('updates services that have an update and clears the selection', () => {
      component['selected'].set([pending, current]);

      component['onUpdateSelected']();

      expect(servicesStore.updateServices).toHaveBeenCalledWith({
        names: ['api'],
      });
      expect(component['selected']()).toEqual([]);
    });
  });

  describe('hasHostJobsDialog', () => {
    it('stays hidden without host job history', () => {
      expect(component['hasHostJobsDialog']()).toBe(false);
    });

    it('shows the dialog when the host has completed jobs', () => {
      selectedHost.set({
        jobState: {
          status: EJobStatus.DONE,
          completed: [{ kind: 'check_services' }],
        },
        pruneResult: null,
      } as IHostEntity);

      expect(component['hasHostJobsDialog']()).toBe(true);
    });
  });

  describe('logs', () => {
    it('replaces an empty response', async () => {
      logs.mockReturnValue(of(''));
      component['openLogs'](pending);
      await fixture.whenStable();

      expect(logs).toHaveBeenCalledWith(7, 'api', 200, false);
      expect(component['logsResource'].value()).toBe('(No logs)');
    });

    it('toasts and shows a fallback when loading fails', async () => {
      const error = new Error('offline');
      logs.mockReturnValue(throwError(() => error));
      component['openLogs'](pending);
      await fixture.whenStable();

      expect(toastService.error).toHaveBeenCalledWith(error);
      expect(component['logsResource'].value()).toBe('(Failed to load logs)');
    });
  });
});
