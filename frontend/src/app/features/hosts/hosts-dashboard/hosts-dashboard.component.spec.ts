import { ComponentFixture, TestBed } from '@angular/core/testing';
import { HostsDashboardComponent } from './hosts-dashboard.component';
import { ActivatedRoute } from '@angular/router';
import { Subject } from 'rxjs';
import { HostsStore } from '../hosts.store';
import { MessageService } from 'primeng/api';
import { provideTranslateService } from '@ngx-translate/core';
import { DialogService } from 'primeng/dynamicdialog';
import { Mocked } from 'vitest';

describe('HostsDashboardComponent', () => {
  let component: HostsDashboardComponent;
  let fixture: ComponentFixture<HostsDashboardComponent>;
  let hostsStore: InstanceType<typeof HostsStore>;

  const activatedRouteParams = new Subject<object>();
  let activatedRouteMock: Partial<Mocked<ActivatedRoute>>;

  beforeEach(async () => {
    activatedRouteMock = {
      params: activatedRouteParams,
      toString: vi.fn(),
    };

    await TestBed.configureTestingModule({
      imports: [HostsDashboardComponent],
      providers: [
        { provide: ActivatedRoute, useValue: activatedRouteMock },
        HostsStore,
        MessageService,
        provideTranslateService(),
        DialogService,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(HostsDashboardComponent);
    component = fixture.componentInstance;
    hostsStore = TestBed.inject(HostsStore);
  });

  it('should create', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it('should select host', () => {
    const selectSpy = vi.spyOn(hostsStore, 'select');
    activatedRouteParams.next({ id: 123 });

    expect(selectSpy).toHaveBeenCalledWith(123);
    expect(selectSpy).toHaveBeenCalledTimes(1);
  });

  it('should de-select host', () => {
    const selectSpy = vi.spyOn(hostsStore, 'select');
    fixture.destroy();

    expect(selectSpy).toHaveBeenCalledWith(null);
    expect(selectSpy).toHaveBeenCalledTimes(1);
  });
});
