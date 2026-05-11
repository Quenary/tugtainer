import { inject } from '@angular/core';
import { Routes } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { authGuard } from './core/guards/auth-guard';
import { first, Observable } from 'rxjs';
import { ContainersStore } from './features/containers/containers.store';
import { ImagesStore } from './features/images/images.store';
import { IRouteData } from '@shared/interfaces/route-data.interface';

const titleTranslate = (titleKey: string) => (): Observable<string> => {
  const translateService = inject(TranslateService);
  return translateService.get(titleKey).pipe(first());
};

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/hosts',
    pathMatch: 'full',
  },
  // UNAUTHORIZED
  {
    path: 'auth',
    title: titleTranslate('NAV.AUTH'),
    loadComponent: () =>
      import('./features/auth/auth.component').then((c) => c.AuthComponent),
  },
  // AUTHORIZED
  {
    path: 'hosts',
    title: titleTranslate('NAV.HOSTS'),
    data: {
      breadcrumb: 'HOSTS',
    } satisfies IRouteData,
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/hosts/hosts.component').then((c) => c.HostsComponent),
    children: [
      {
        path: ':id/edit',
        data: {
          breadcrumbIcon: 'pi pi-server',
        } satisfies IRouteData,
        loadComponent: () =>
          import('./features/hosts/hosts-card/hosts-card.component').then(
            (c) => c.HostsCardComponent,
          ),
      },
      {
        path: ':id',
        data: {
          breadcrumb: 'DASHBOARD',
        } satisfies IRouteData,
        loadComponent: () =>
          import('./features/hosts/hosts-dashboard/hosts-dashboard.component').then(
            (c) => c.HostsDashboardComponent,
          ),
        children: [
          {
            path: 'containers',
            title: titleTranslate('NAV.CONTAINERS'),
            data: {
              breadcrumb: 'CONTAINERS',
            } satisfies IRouteData,
            loadComponent: () =>
              import('./features/containers/containers.component').then(
                (c) => c.ContainersComponent,
              ),
            providers: [ContainersStore],
            children: [
              {
                path: ':containerNameOrId',
                data: {
                  breadcrumbIcon: 'pi pi-box',
                } satisfies IRouteData,
                loadComponent: () =>
                  import('./features/container-card/container-card.component').then(
                    (c) => c.ContainerCardComponent,
                  ),
              },
            ],
          },
          {
            path: 'images',
            title: titleTranslate('NAV.IMAGES'),
            data: {
              breadcrumb: 'IMAGES',
            } satisfies IRouteData,
            loadComponent: () =>
              import('./features/images/images.component').then(
                (c) => c.ImagesComponent,
              ),
            providers: [ImagesStore],
            children: [
              {
                path: ':imageId',
                data: {
                  breadcrumbIcon: 'pi pi-list',
                } satisfies IRouteData,
                loadComponent: () =>
                  import('./features/image-card/image-card.component').then(
                    (c) => c.ImageCardComponent,
                  ),
              },
            ],
          },
        ],
      },
    ],
  },
  {
    path: 'settings',
    title: titleTranslate('NAV.SETTINGS'),
    data: {
      breadcrumb: 'SETTINGS',
    } satisfies IRouteData,
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/settings/settings.component').then(
        (c) => c.SettingsComponent,
      ),
  },
];
