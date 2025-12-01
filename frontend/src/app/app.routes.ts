import { inject } from '@angular/core';
import { Routes } from '@angular/router';
import { TranslateService } from '@ngx-translate/core';
import { authGuard } from './core/guards/auth-guard';
import { first, Observable } from 'rxjs';

const titleTranslate = (titleKey: string) => (): Observable<string> => {
  const translateService = inject(TranslateService);
  return translateService.get(titleKey).pipe(first());
};

export const routes: Routes = [
  {
    path: '',
    redirectTo: '/containers',
    pathMatch: 'full',
  },
  // UNAUTHORIZED
  {
    path: 'auth',
    title: titleTranslate('NAV.AUTH'),
    loadComponent: () => import('./features/auth-page/auth-page').then((c) => c.AuthPage),
  },
  // AUTHORIZED
  {
    path: 'hosts',
    title: titleTranslate('NAV.HOSTS'),
    canActivate: [authGuard],
    loadComponent: () => import('./features/hosts-page/hosts-page').then((c) => c.HostsPage),
    children: [
      {
        path: ':id',
        loadComponent: () =>
          import('./features/hosts-page/hosts-page-card/hosts-page-card').then(
            (c) => c.HostsPageCard,
          ),
      },
      {
        path: ':hostId/:containerNameOrId',
        loadComponent: () =>
          import('./features/container-card/container-card').then((c) => c.ContainerCard),
      },
    ],
  },
  {
    path: 'containers',
    title: titleTranslate('NAV.CONTAINERS'),
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/containers-page/containers-page').then((c) => c.ContainersPage),
  },
  {
    path: 'images',
    title: titleTranslate('NAV.IMAGES'),
    canActivate: [authGuard],
    loadComponent: () => import('./features/images-page/images-page').then((c) => c.ImagesPage),
  },
  {
    path: 'settings',
    title: titleTranslate('NAV.SETTINGS'),
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/settings-page/settings-page').then((c) => c.SettingsPage),
  },
];
