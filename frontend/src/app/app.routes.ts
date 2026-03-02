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
    loadComponent: () => import('./features/auth/auth.component').then((c) => c.AuthComponent),
  },
  // AUTHORIZED
  {
    path: 'hosts',
    title: titleTranslate('NAV.HOSTS'),
    canActivate: [authGuard],
    loadComponent: () => import('./features/hosts/hosts.component').then((c) => c.HostsComponent),
    children: [
      {
        path: ':id',
        loadComponent: () =>
          import('./features/hosts/hosts-card/hosts-card.component').then(
            (c) => c.HostsCardComponent,
          ),
      },
      {
        path: ':hostId/:containerNameOrId',
        loadComponent: () =>
          import('./features/container-card/container-card.component').then(
            (c) => c.ContainerCardComponent,
          ),
      },
    ],
  },
  {
    path: 'containers',
    title: titleTranslate('NAV.CONTAINERS'),
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/containers/containers.component').then((c) => c.ContainersComponent),
  },
  {
    path: 'images',
    title: titleTranslate('NAV.IMAGES'),
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/images/images.component').then((c) => c.ImagesComponent),
  },
  {
    path: 'settings',
    title: titleTranslate('NAV.SETTINGS'),
    canActivate: [authGuard],
    loadComponent: () =>
      import('./features/settings/settings.component').then((c) => c.SettingsComponent),
  },
];
