import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BreakpointObserver, BreakpointState } from '@angular/cdk/layout';
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
  const breakpointObserverObserve = new Subject<BreakpointState>();
  let activatedRouteMock: Partial<Mocked<ActivatedRoute>>;
  let breakpointObserverMock: Partial<Mocked<BreakpointObserver>>;

  beforeEach(async () => {
    activatedRouteMock = {
      params: activatedRouteParams,
      toString: vi.fn(),
    };
    breakpointObserverMock = {
      observe: vi.fn().mockReturnValue(breakpointObserverObserve),
    };

    await TestBed.configureTestingModule({
      imports: [HostsDashboardComponent],
      providers: [
        { provide: ActivatedRoute, useValue: activatedRouteMock },
        { provide: BreakpointObserver, useValue: breakpointObserverMock },
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

  it('should update narrow state', () => {
    breakpointObserverObserve.next({ matches: true } as BreakpointState);
    fixture.detectChanges();
    expect(component['narrow']()).toBe(true);
    expect(fixture.nativeElement.classList.contains('narrow')).toBe(true);

    breakpointObserverObserve.next({ matches: false } as BreakpointState);
    fixture.detectChanges();
    expect(component['narrow']()).toBe(false);
    expect(fixture.nativeElement.classList.contains('narrow')).toBe(false);

    component['narrow'].set(true);
    fixture.detectChanges();
    expect(component['narrow']()).toBe(true);
    expect(fixture.nativeElement.classList.contains('narrow')).toBe(true);
  });
});
