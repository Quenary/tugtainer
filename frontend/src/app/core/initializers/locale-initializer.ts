import { LOCATION_INITIALIZED } from '@angular/common';
import { inject, EnvironmentInjector } from '@angular/core';
import {
  getStoredLang,
  LocaleService,
  resolveLocale,
} from '../services/locale.service';

export const localeInitializer = async () => {
  const environmentInjector = inject(EnvironmentInjector);
  const localeService = inject(LocaleService);
  const locationInitialized = environmentInjector.get(
    LOCATION_INITIALIZED,
    Promise.resolve(null),
  );
  await locationInitialized;
  await localeService.apply(resolveLocale(getStoredLang()));
};
