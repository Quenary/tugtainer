import {
  Component,
  provideZonelessChangeDetection,
  signal,
} from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { App } from './app';
import { provideRouter } from '@angular/router';
import { ToastService } from './core/services/toast.service';
import { provideTranslateService } from '@ngx-translate/core';
import {
  IsUpdateAvailableResponseBody,
  IVersion,
} from './features/public/public-interface';
import { RouterTestingHarness } from '@angular/router/testing';
import { Mocked } from 'vitest';
import { getToastServiceMock } from '@testing/mocks/toast-service.mock';
import { AppStore } from './app.store';
import { DeepSignal } from '@ngrx/signals';
import { MenuComponent } from '@shared/components/menu/menu.component';
import { MessageService } from 'primeng/api';

@Component({
  selector: 'app-test-comp',
  standalone: true,
  template: '',
})
class TestComponent {}

@Component({
  selector: 'app-menu',
  standalone: true,
  template: '',
})
class MenuTestComponent {}

describe('App', () => {
  let fixture: ComponentFixture<App>;
  let component: App;

  let harness: RouterTestingHarness;
  let toastServiceMock: Mocked<ToastService>;
  let appStoreMock: Partial<InstanceType<typeof AppStore>>;

  beforeEach(async () => {
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
        { provide: AppStore, useValue: appStoreMock },
        { provide: ToastService, useValue: toastServiceMock },
        MessageService,
        provideRouter([
          {
            path: '',
            pathMatch: 'full',
            redirectTo: '/hosts',
          },
          {
            path: 'hosts',
            component: TestComponent,
          },
          {
            path: 'auth',
            component: TestComponent,
          },
        ]),
      ],
    })
      .overrideComponent(App, {
        remove: {
          imports: [MenuComponent],
        },
        add: {
          imports: [MenuTestComponent],
        },
      })
      .compileComponents();

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
    await harness.navigateByUrl('/hosts');
    expect(component['isToolbarVisible']()).toBe(true);
  });
});
