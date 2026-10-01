import {
  Component,
  provideZonelessChangeDetection,
  signal,
} from '@angular/core';
import { ComponentFixture, TestBed } from '@angular/core/testing';
import { App } from './app';
import { provideRouter, RouterOutlet, Routes } from '@angular/router';
import { ToastService } from './core/services/toast.service';
import { provideTranslateService, TranslateService } from '@ngx-translate/core';
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
import { MenuItem, MessageService } from '@openng/optimus-ui/api';
import { IRouteData } from '@shared/interfaces/route-data.interface';

@Component({
  selector: 'app-test-comp',
  standalone: true,
  imports: [RouterOutlet],
  template: '<router-outlet />',
})
class TestComponent {}

const breadcrumbLabels = {
  HOSTS: 'Hosts',
  DASHBOARD: 'Dashboard',
  CONTAINERS: 'Containers',
  IMAGES: 'Images',
  SERVICES: 'Services',
  HEALTH_HISTORY: 'Healthcheck Monitoring',
  SETTINGS: 'Settings',
};

const routes: Routes = [
  {
    path: '',
    pathMatch: 'full',
    redirectTo: '/hosts',
  },
  {
    path: 'auth',
    component: TestComponent,
  },
  {
    path: 'hosts',
    component: TestComponent,
    data: { breadcrumb: 'HOSTS' } satisfies IRouteData,
    children: [
      {
        path: ':id/edit',
        component: TestComponent,
        data: { breadcrumbIcon: 'pi pi-server' } satisfies IRouteData,
      },
      {
        path: ':id',
        component: TestComponent,
        data: { breadcrumb: 'DASHBOARD' } satisfies IRouteData,
        children: [
          {
            path: 'containers',
            component: TestComponent,
            data: { breadcrumb: 'CONTAINERS' } satisfies IRouteData,
            children: [
              {
                path: ':containerNameOrId',
                component: TestComponent,
                data: { breadcrumbIcon: 'pi pi-box' } satisfies IRouteData,
              },
            ],
          },
          {
            path: 'images',
            component: TestComponent,
            data: { breadcrumb: 'IMAGES' } satisfies IRouteData,
            children: [
              {
                path: ':imageId',
                component: TestComponent,
                data: { breadcrumbIcon: 'pi pi-list' } satisfies IRouteData,
              },
            ],
          },
          {
            path: 'services',
            component: TestComponent,
            data: { breadcrumb: 'SERVICES' } satisfies IRouteData,
          },
          {
            path: 'health',
            component: TestComponent,
            data: { breadcrumb: 'HEALTH_HISTORY' } satisfies IRouteData,
          },
        ],
      },
    ],
  },
  {
    path: 'settings',
    component: TestComponent,
    data: { breadcrumb: 'SETTINGS' } satisfies IRouteData,
  },
];

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
  let translateService: TranslateService;

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
        provideRouter(routes),
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

    translateService = TestBed.inject(TranslateService);
    translateService.setTranslation('en', { BREADCRUMBS: breadcrumbLabels });
    translateService.use('en');

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

  describe('breadcrumbs', () => {
    function readBreadcrumbs(): MenuItem[] {
      fixture.detectChanges();
      return component['breadcrumbs']();
    }

    it('should keep breadcrumbs empty on routes without breadcrumb data', async () => {
      fixture.detectChanges();
      await harness.navigateByUrl('/auth');

      expect(readBreadcrumbs()).toEqual([]);
    });

    it('should build breadcrumbs for a single route', async () => {
      fixture.detectChanges();
      await harness.navigateByUrl('/settings');

      expect(readBreadcrumbs()).toEqual([
        { label: 'Settings', icon: undefined, routerLink: '/settings' },
      ]);
    });

    it('should build nested breadcrumbs with accumulated router links', async () => {
      fixture.detectChanges();
      await harness.navigateByUrl('/hosts/7/containers/nginx');

      expect(readBreadcrumbs()).toEqual([
        { label: 'Hosts', icon: undefined, routerLink: '/hosts' },
        { label: 'Dashboard', icon: undefined, routerLink: '/hosts/7' },
        {
          label: 'Containers',
          icon: undefined,
          routerLink: '/hosts/7/containers',
        },
        {
          label: undefined,
          icon: 'pi pi-box',
          routerLink: '/hosts/7/containers/nginx',
        },
      ]);
    });

    it('should build breadcrumbs for host sections', async () => {
      fixture.detectChanges();

      await harness.navigateByUrl('/hosts');
      expect(readBreadcrumbs()).toEqual([
        { label: 'Hosts', icon: undefined, routerLink: '/hosts' },
      ]);

      await harness.navigateByUrl('/hosts/3/edit');
      expect(readBreadcrumbs()).toEqual([
        { label: 'Hosts', icon: undefined, routerLink: '/hosts' },
        {
          label: undefined,
          icon: 'pi pi-server',
          routerLink: '/hosts/3/edit',
        },
      ]);

      await harness.navigateByUrl('/hosts/3/images/sha256');
      expect(readBreadcrumbs()).toEqual([
        { label: 'Hosts', icon: undefined, routerLink: '/hosts' },
        { label: 'Dashboard', icon: undefined, routerLink: '/hosts/3' },
        { label: 'Images', icon: undefined, routerLink: '/hosts/3/images' },
        {
          label: undefined,
          icon: 'pi pi-list',
          routerLink: '/hosts/3/images/sha256',
        },
      ]);

      await harness.navigateByUrl('/hosts/3/services');
      expect(readBreadcrumbs()).toEqual([
        { label: 'Hosts', icon: undefined, routerLink: '/hosts' },
        { label: 'Dashboard', icon: undefined, routerLink: '/hosts/3' },
        {
          label: 'Services',
          icon: undefined,
          routerLink: '/hosts/3/services',
        },
      ]);

      await harness.navigateByUrl('/hosts/3/health');
      expect(readBreadcrumbs()).toEqual([
        { label: 'Hosts', icon: undefined, routerLink: '/hosts' },
        { label: 'Dashboard', icon: undefined, routerLink: '/hosts/3' },
        {
          label: 'Healthcheck Monitoring',
          icon: undefined,
          routerLink: '/hosts/3/health',
        },
      ]);
    });

    it('should refresh breadcrumb labels when translations change', async () => {
      fixture.detectChanges();
      await harness.navigateByUrl('/settings');
      expect(readBreadcrumbs()).toEqual([
        { label: 'Settings', icon: undefined, routerLink: '/settings' },
      ]);

      translateService.setTranslation('ru', {
        BREADCRUMBS: { ...breadcrumbLabels, SETTINGS: 'Настройки' },
      });
      translateService.use('ru');

      expect(readBreadcrumbs()).toEqual([
        { label: 'Настройки', icon: undefined, routerLink: '/settings' },
      ]);
    });
  });
});
