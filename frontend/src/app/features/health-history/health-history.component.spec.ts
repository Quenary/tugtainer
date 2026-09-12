import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HealthHistoryComponent } from './health-history.component';
import { HostsStore } from '../hosts/hosts.store';
import { TranslateModule } from '@ngx-translate/core';
import { signal, WritableSignal } from '@angular/core';
import { TableLazyLoadEvent } from 'primeng/table';
import { HealthHistoryApiService } from './health-history-api.service';
import { of } from 'rxjs';
import { Mocked } from 'vitest';
import { getHealthHistoryApiServiceMock } from '@testing/mocks/health-history-api.service.mock';
import { provideRouter } from '@angular/router';

describe('HealthHistoryComponent', () => {
  let component: HealthHistoryComponent;
  let fixture: ComponentFixture<HealthHistoryComponent>;
  let hostsStoreMock: Partial<InstanceType<typeof HostsStore>>;
  let healthHistoryApiServiceMock: Mocked<HealthHistoryApiService>;
  let hostSelectedIdSignal: WritableSignal<number | null>;

  beforeEach(async () => {
    hostSelectedIdSignal = signal<number | null>(null);
    hostsStoreMock = { selectedId: hostSelectedIdSignal };
    healthHistoryApiServiceMock = getHealthHistoryApiServiceMock();
    healthHistoryApiServiceMock.getHistory.mockReturnValue(
      of({ items: [], total: 0, page: 1, limit: 20 }),
    );

    await TestBed.configureTestingModule({
      imports: [HealthHistoryComponent, TranslateModule.forRoot()],
      providers: [
        provideRouter([]),
        { provide: HostsStore, useValue: hostsStoreMock },
        {
          provide: HealthHistoryApiService,
          useValue: healthHistoryApiServiceMock,
        },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(HealthHistoryComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it('should not load history on init if no hostId is selected', async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    expect(healthHistoryApiServiceMock.getHistory).not.toHaveBeenCalled();
  });

  it('should load history when hostId is selected', async () => {
    hostSelectedIdSignal.set(1);
    fixture.detectChanges();
    await fixture.whenStable();

    expect(healthHistoryApiServiceMock.getHistory).toHaveBeenCalledWith({
      host_id: 1,
      page: 1,
      limit: 25,
    });
  });

  it('should load history on lazy load', async () => {
    hostSelectedIdSignal.set(1);
    fixture.detectChanges();
    await fixture.whenStable();
    healthHistoryApiServiceMock.getHistory.mockClear();

    const event: TableLazyLoadEvent = { first: 40, rows: 20 };
    component.onLazyLoad(event);
    fixture.detectChanges();
    await fixture.whenStable();

    expect(healthHistoryApiServiceMock.getHistory).toHaveBeenCalledWith({
      host_id: 1,
      page: 3,
      limit: 20,
    });
  });

  it('should filter by status and reset page to 1', async () => {
    hostSelectedIdSignal.set(1);
    fixture.detectChanges();
    await fixture.whenStable();
    healthHistoryApiServiceMock.getHistory.mockClear();

    component.onStatusChange('unhealthy');
    fixture.detectChanges();
    await fixture.whenStable();

    expect(healthHistoryApiServiceMock.getHistory).toHaveBeenCalledWith({
      host_id: 1,
      page: 1,
      limit: 25,
      status: ['unhealthy'],
    });
  });
});
