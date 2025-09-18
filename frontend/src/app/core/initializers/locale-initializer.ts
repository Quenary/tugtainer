import { LOCATION_INITIALIZED, registerLocaleData } from '@angular/common';
import { inject, EnvironmentInjector } from '@angular/core';
import { from, switchMap, first, catchError, of, tap } from 'rxjs';

const importLocale = (locale: string) => {
  let _import: Promise<any> = import('@angular/common/locales/en');
  locale = locale.split('-')[0];
  switch (locale) {
    case 'ru':
      _import = import('@angular/common/locales/ru');
      break;
    case 'de':
      _import = import('@angular/common/locales/de');
      break;
    case 'fr':
      _import = import('@angular/common/locales/fr');
      break;
    case 'ja':
      _import = import('@angular/common/locales/ja');
      break;
    case 'it':
      _import = import('@angular/common/locales/it');
      break;
    case 'es':
      _import = import('@angular/common/locales/es');
      break;
    case 'zh':
      _import = import('@angular/common/locales/zh');
      break;
  }
  return from(_import.then((c) => c.default));
};

export const localeInitializer = () => {
  const environmentInjector = inject(EnvironmentInjector);
  const locationInitialized = environmentInjector.get(LOCATION_INITIALIZED, Promise.resolve(null));
  return from(locationInitialized).pipe(
    switchMap(() => {
      let lang = navigator.language || 'en';
      return importLocale(lang).pipe(
        tap((data) => {
          registerLocaleData(data);
        }),
        first(),
        catchError(() => of(null))
      );
    })
  );
};
