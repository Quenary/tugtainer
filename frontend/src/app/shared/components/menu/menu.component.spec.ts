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

describe('MenuComponent', () => {
  let component: MenuComponent;
  let fixture: ComponentFixture<MenuComponent>;

  const breakpointObserverObserve = new Subject<BreakpointState>();
  let appStoreMock: jasmine.SpyObj<InstanceType<typeof AppStore>>;
  let breakpointObserverSpy: jasmine.SpyObj<BreakpointObserver>;
  let authApiServiceMock: jasmine.SpyObj<AuthApiService>;

  beforeEach(async () => {
    appStoreMock = jasmine.createSpyObj<InstanceType<typeof AppStore>>(
      'AppStore',
      ['setTheme'],
      { theme: signal('AUTO') },
    );
    breakpointObserverSpy = jasmine.createSpyObj<BreakpointObserver>(
      'BreakpointObserver',
      [],
      {
        observe: () => breakpointObserverObserve,
      },
    );
    authApiServiceMock = jasmine.createSpyObj<AuthApiService>(
      'AuthApiService',
      ['logout'],
    );

    await TestBed.configureTestingModule({
      imports: [MenuComponent],
      providers: [
        { provide: AppStore, useValue: appStoreMock },
        provideTranslateService(),
        { provide: BreakpointObserver, useValue: breakpointObserverSpy },
        { provide: AuthApiService, useValue: authApiServiceMock },
        provideRouter([]),
        MessageService,
        HostsStore,
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
    expect(component['narrow']()).toBeTrue();

    breakpointObserverObserve.next({ matches: false } as BreakpointState);
    expect(component['narrow']()).toBeFalse();

    component['narrow'].set(true);
    expect(component['narrow']()).toBeTrue();

    breakpointObserverObserve.next({ matches: true } as BreakpointState);
    expect(component['narrow']()).toBeTrue();
  });

  it('should logout and navigate', () => {
    const router = TestBed.inject(Router);
    const navigateSpy = spyOn(router, 'navigate');

    authApiServiceMock.logout.and.returnValue(of(null));
    component['logout']();
    expect(navigateSpy).toHaveBeenCalledWith(['/auth']);
  });
});
