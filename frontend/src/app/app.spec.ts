import { Component, DebugElement, provideZonelessChangeDetection } from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { App } from './app';
import { AuthApiService } from './features/auth/auth-api.service';
import { PublicApiService } from './features/public/public-api.service';
import { ActivatedRoute, provideRouter, Router, Event as RouterEvent } from '@angular/router';
import { ToastService } from './core/services/toast.service';
import { provideTranslateService } from '@ngx-translate/core';
import { of, Subject } from 'rxjs';
import { IsUpdateAvailableResponseBody } from './features/public/public-interface';
import { MessageService } from 'primeng/api';
import { RouterTestingHarness } from '@angular/router/testing';

@Component({
  selector: 'test-comp',
  standalone: true,
  template: '',
})
class TestComponent {}

describe('App', () => {
  let fixture: ComponentFixture<App>;
  let component: App;
  let de: DebugElement;

  let harness: RouterTestingHarness;
  let authApiServiceMock: jasmine.SpyObj<AuthApiService>;
  let publicApiServiceMock: jasmine.SpyObj<PublicApiService>;
  let routerMock: jasmine.SpyObj<Router>;
  let activatedRouteMock: jasmine.SpyObj<ActivatedRoute>;
  let toastServiceMock: jasmine.SpyObj<ToastService>;
  const routerEvents$ = new Subject<RouterEvent>();

  beforeEach(async () => {
    authApiServiceMock = jasmine.createSpyObj<AuthApiService>('AuthApiService', ['initiateLogin'], {
      isAuthorized: jasmine.createSpy('isAuthorized').and.returnValue(of(null)),
      isDisabled: jasmine.createSpy('isDisabled').and.returnValue(of(false)),
      logout: jasmine.createSpy('isPasswordSet').and.returnValue(of({})),
    });
    publicApiServiceMock = jasmine.createSpyObj('PublicApiService', [], {
      getVersion: jasmine.createSpy('getVersion').and.returnValue(of({ image_version: '1.2.3' })),
      isUpdateAvailable: jasmine.createSpy('isUpdateAvailable').and.returnValue(
        of({
          is_available: false,
          release_url: null,
        } satisfies IsUpdateAvailableResponseBody),
      ),
    });
    routerMock = jasmine.createSpyObj<Router>('Router', ['navigate', 'url', 'createUrlTree'], {
      events: routerEvents$,
    });
    activatedRouteMock = jasmine.createSpyObj<ActivatedRoute>('ActivatedRoute', ['snapshot']);
    toastServiceMock = jasmine.createSpyObj('ToastService', ['success', 'error']);

    await TestBed.configureTestingModule({
      imports: [App],
      providers: [
        provideZonelessChangeDetection(),
        provideTranslateService(),
        { provide: AuthApiService, useValue: authApiServiceMock },
        { provide: PublicApiService, useValue: publicApiServiceMock },
        { provide: ToastService, useValue: toastServiceMock },
        provideRouter([
          {
            path: '',
            pathMatch: 'full',
            redirectTo: '/containers',
          },
          {
            path: 'containers',
            component: TestComponent,
          },
          {
            path: 'auth',
            component: TestComponent,
          },
        ]),
        MessageService,
      ],
    }).compileComponents();

    harness = await RouterTestingHarness.create();
    fixture = TestBed.createComponent(App);
    component = fixture.componentInstance;
    de = fixture.debugElement;
  });

  it('should create the app', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it('should hide toolbar', async () => {
    fixture.detectChanges();
    await harness.navigateByUrl('/auth');
    expect(component['isToolbarVisible']()).toBeFalse();
  });

  it('should show toolbar', async () => {
    fixture.detectChanges();
    await harness.navigateByUrl('/containers');
    expect(component['isToolbarVisible']()).toBeTrue();
  });

  // TODO add more tests
});
