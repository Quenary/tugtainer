import { ComponentFixture, TestBed } from '@angular/core/testing';
import { BreakpointObserver, BreakpointState } from '@angular/cdk/layout';
import { MenuComponent } from './menu.component';
import { AppStore } from 'src/app/app.store';
import { provideTranslateService } from '@ngx-translate/core';
import { AuthApiService } from 'src/app/features/auth/auth-api.service';
import { provideRouter, Router } from '@angular/router';
import { MessageService } from 'primeng/api';
import { HostsStore } from 'src/app/features/hosts/hosts.store';
import { signal } from '@angular/core';
import { of, Subject } from 'rxjs';
import { DialogService } from 'primeng/dynamicdialog';
import { Mocked } from 'vitest';
import { getAuthApiServiceMock } from '@testing/mocks/auth-api.service.mock';

describe('MenuComponent', () => {
  let component: MenuComponent;
  let fixture: ComponentFixture<MenuComponent>;

  const breakpointObserverObserve = new Subject<BreakpointState>();
  let appStoreMock: Partial<InstanceType<typeof AppStore>>;
  let breakpointObserverMock: Partial<Mocked<BreakpointObserver>>;
  let authApiServiceMock: Mocked<AuthApiService>;

  beforeEach(async () => {
    appStoreMock = {
      setTheme: vi.fn(),
      theme: signal('AUTO'),
    };
    breakpointObserverMock = {
      observe: vi.fn().mockReturnValue(breakpointObserverObserve),
    };
    authApiServiceMock = getAuthApiServiceMock();

    await TestBed.configureTestingModule({
      imports: [MenuComponent],
      providers: [
        { provide: AppStore, useValue: appStoreMock },
        provideTranslateService(),
        { provide: BreakpointObserver, useValue: breakpointObserverMock },
        { provide: AuthApiService, useValue: authApiServiceMock },
        provideRouter([]),
        MessageService,
        HostsStore,
        DialogService,
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(MenuComponent);
    component = fixture.componentInstance;
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });

  it('should update narrow state', () => {
    breakpointObserverObserve.next({ matches: true } as BreakpointState);
    expect(component['narrow']()).toBe(true);

    breakpointObserverObserve.next({ matches: false } as BreakpointState);
    expect(component['narrow']()).toBe(false);

    component['narrow'].set(true);
    expect(component['narrow']()).toBe(true);

    breakpointObserverObserve.next({ matches: true } as BreakpointState);
    expect(component['narrow']()).toBe(true);
  });

  it('should logout and navigate', () => {
    const router = TestBed.inject(Router);
    const navigateSpy = vi.spyOn(router, 'navigate');

    authApiServiceMock.logout.mockReturnValue(of(null));
    component['logout']();
    expect(navigateSpy).toHaveBeenCalledWith(['/auth']);
  });
});
