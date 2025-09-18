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
    redirectTo: '/home',
    pathMatch: 'full',
  },
  // UNAUTHORIZED
  {
    path: 'auth',
    title: titleTranslate('NAV.AUTH'),
    loadComponent: () => import('./features/auth/auth').then((c) => c.Auth),
  },
  // AUTHORIZED
  {
    path: 'home',
    title: titleTranslate('NAV.HOME'),
    canActivate: [authGuard],
    loadComponent: () => import('./features/home/home').then((c) => c.Home),
  },
];
