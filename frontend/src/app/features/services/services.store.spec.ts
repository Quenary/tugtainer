import { TestBed } from '@angular/core/testing';
import { signal, WritableSignal } from '@angular/core';
import { of, throwError } from 'rxjs';
import { describe, it, expect, beforeEach, vi, Mocked } from 'vitest';
import { ServicesStore } from './services.store';
import { ServicesApiService } from './services-api.service';
import { ToastService } from 'src/app/core/services/toast.service';
import { HostsStore, IHostEntity } from '../hosts/hosts.store';
import { IServiceListItem } from './services.interface';
import { getToastServiceMock } from '@testing/mocks/toast-service.mock';
import { TranslateService } from '@ngx-translate/core';

describe('ServicesStore', () => {
  let store: InstanceType<typeof ServicesStore>;
  let servicesApiServiceMock: {
    list: ReturnType<typeof vi.fn>;
    patch: ReturnType<typeof vi.fn>;
    check: ReturnType<typeof vi.fn>;
    update: ReturnType<typeof vi.fn>;
    logs: ReturnType<typeof vi.fn>;
  };
  let toastServiceMock: Mocked<ToastService>;
  let hostsStoreMock: Partial<InstanceType<typeof HostsStore>>;

  let hostSelectedIdSignal: WritableSignal<number | null>;
  let hostSelectedSignal: WritableSignal<IHostEntity | null>;
  let updateServicesListSignal: WritableSignal<Date | null>;

  const mockHost = {
    id: 1,
    name: 'Host 1',
    is_swarm: true,
  } as IHostEntity;

  const mockService: IServiceListItem = {
    id: 'svc-1',
    name: 'web-service',
    image: 'nginx:latest',
    mode: 'replicated',
    replicas_running: 2,
    replicas_desired: 2,
    check_enabled: true,
    update_enabled: true,
    update_available: false,
    checked_at: null,
    updated_at: null,
    update_status_state: null,
    update_status_message: null,
    labels: {},
  };

  beforeEach(() => {
    servicesApiServiceMock = {
      list: vi.fn().mockReturnValue(of([mockService])),
      patch: vi
        .fn()
        .mockReturnValue(of({ ...mockService, check_enabled: false })),
      check: vi.fn().mockReturnValue(of({ detail: 'Check job submitted' })),
      update: vi.fn().mockReturnValue(of({ detail: 'Update job submitted' })),
      logs: vi.fn().mockReturnValue(of('Service log output')),
    };

    toastServiceMock = getToastServiceMock();

    hostSelectedIdSignal = signal(1);
    hostSelectedSignal = signal(mockHost);
    updateServicesListSignal = signal<Date | null>(null);
    hostsStoreMock = {
      selectedId: hostSelectedIdSignal,
      selected: hostSelectedSignal,
      updateServicesList: updateServicesListSignal,
    };

    TestBed.configureTestingModule({
      providers: [
        ServicesStore,
        {
          provide: ServicesApiService,
          useValue: servicesApiServiceMock,
        },
        {
          provide: ToastService,
          useValue: toastServiceMock,
        },
        {
          provide: HostsStore,
          useValue: hostsStoreMock,
        },
        {
          provide: TranslateService,
          useValue: {
            instant: vi.fn((key: string) => key),
          },
        },
      ],
    });

    store = TestBed.inject(ServicesStore);
  });

  it('should initialize with empty state', () => {
    expect(store.entities()).toEqual([]);
    expect(store.loading()).toBe(false);
    expect(store.selectedName()).toBeNull();
    expect(store.hostId()).toBe(1);
  });

  it('should load list of services', () => {
    store.loadList();

    expect(servicesApiServiceMock.list).toHaveBeenCalledWith(1);
    expect(store.entities()).toHaveLength(1);
    expect(store.entities()[0].name).toBe('web-service');
  });

  it('should handle load error gracefully', () => {
    const error = new Error('Failed to load services');
    servicesApiServiceMock.list.mockReturnValue(throwError(() => error));

    store.loadList();

    expect(toastServiceMock.error).toHaveBeenCalledWith(error);
  });

  it('should patch service', () => {
    store.loadList();

    store.patchService({
      serviceName: 'web-service',
      body: { check_enabled: false },
    });

    expect(servicesApiServiceMock.patch).toHaveBeenCalledWith(
      1,
      'web-service',
      {
        check_enabled: false,
      },
    );
    expect(store.entityMap()['web-service'].check_enabled).toBe(false);
  });

  it('should trigger checkServices', () => {
    store.checkServices({ names: ['web-service'] });

    expect(servicesApiServiceMock.check).toHaveBeenCalledWith(1, [
      'web-service',
    ]);
    expect(toastServiceMock.success).toHaveBeenCalled();
  });

  it('should trigger updateServices', () => {
    store.updateServices({ names: ['web-service'] });

    expect(servicesApiServiceMock.update).toHaveBeenCalledWith(1, [
      'web-service',
    ]);
    expect(toastServiceMock.success).toHaveBeenCalled();
  });

  it('should select a service by name', () => {
    store.loadList();

    store.select('web-service');
    expect(store.selected()?.name).toBe('web-service');

    store.select(null);
    expect(store.selected()).toBeNull();
  });

  describe('updateServicesList effect', () => {
    it('should reload list when updateServicesList changes', () => {
      updateServicesListSignal.set(new Date());
      TestBed.flushEffects();
      expect(servicesApiServiceMock.list).toHaveBeenCalled();
    });

    it('should not reload if updateServicesList is null', () => {
      servicesApiServiceMock.list.mockClear();
      updateServicesListSignal.set(null);
      TestBed.flushEffects();
      expect(servicesApiServiceMock.list).not.toHaveBeenCalled();
    });
  });
});
