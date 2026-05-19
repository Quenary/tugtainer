import {
  Component,
  provideZonelessChangeDetection,
  signal,
} from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { App } from './app';
import { AuthApiService } from './features/auth/auth-api.service';
import { provideRouter } from '@angular/router';
import { ToastService } from './core/services/toast.service';
import { provideTranslateService } from '@ngx-translate/core';
import { of } from 'rxjs';
import {
  IsUpdateAvailableResponseBody,
  IVersion,
} from './features/public/public-interface';
import { MessageService } from 'primeng/api';
import { RouterTestingHarness } from '@angular/router/testing';
import { DialogService } from 'primeng/dynamicdialog';
import { Mocked } from 'vitest';
import { getToastServiceMock } from '@testing/mocks/toast-service.mock';
import { AppStore } from './app.store';
import { DeepSignal } from '@ngrx/signals';
import { getAuthApiServiceMock } from '@testing/mocks/auth-api.service.mock';

@Component({
  selector: 'app-test-comp',
  standalone: true,
  template: '',
})
class TestComponent {}

describe('App', () => {
  let fixture: ComponentFixture<App>;
  let component: App;

  let harness: RouterTestingHarness;
  let authApiServiceMock: Mocked<AuthApiService>;
  let toastServiceMock: Mocked<ToastService>;
  let appStoreMock: Partial<InstanceType<typeof AppStore>>;

  beforeEach(async () => {
    authApiServiceMock = getAuthApiServiceMock();
    authApiServiceMock.isAuthorized.mockReturnValue(of(null));
    authApiServiceMock.isDisabled.mockReturnValue(of(false));
    authApiServiceMock.logout.mockReturnValue(of({}));

    appStoreMock = {
      version: signal({
        image_version: '1.2.3',
      }) as unknown as DeepSignal<IVersion>,
      update: signal({
        is_available: false,
        release_url: null,
      }) as unknown as DeepSignal<IsUpdateAvailableResponseBody>,
      setTheme: vi.fn(),
      theme: signal('AUTO'),
      isAuthDisabled: signal(false),
    };

    toastServiceMock = getToastServiceMock();

    await TestBed.configureTestingModule({
      imports: [App],
      providers: [
        provideZonelessChangeDetection(),
        provideTranslateService(),
        { provide: AuthApiService, useValue: authApiServiceMock },
        { provide: AppStore, useValue: appStoreMock },
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
        DialogService,
      ],
    }).compileComponents();

    harness = await RouterTestingHarness.create();
    fixture = TestBed.createComponent(App);
    component = fixture.componentInstance;
  });

  it('should create the app', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  it('should hide toolbar', async () => {
    fixture.detectChanges();
    await harness.navigateByUrl('/auth');
    expect(component['isToolbarVisible']()).toBe(false);
  });

  it('should show toolbar', async () => {
    fixture.detectChanges();
    await harness.navigateByUrl('/containers');
    expect(component['isToolbarVisible']()).toBe(true);
  });

  // TODO add more tests
});
