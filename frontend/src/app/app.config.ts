import {
  ApplicationConfig,
  LOCALE_ID,
  provideAppInitializer,
  provideBrowserGlobalErrorListeners,
  provideZonelessChangeDetection,
} from '@angular/core';
import { provideRouter } from '@angular/router';
import { routes } from './app.routes';
import { authInterceptor } from './core/interceptors/auth-interceptor';
import { provideHttpClient, withInterceptors } from '@angular/common/http';
import { provideTranslateLoader, provideTranslateService } from '@ngx-translate/core';
import { localeInitializer } from './core/initializers/locale-initializer';
import { providePrimeNG } from 'primeng/config';
import Aura from '@primeuix/themes/aura';
import { provideAnimations } from '@angular/platform-browser/animations';
import { MessageService } from 'primeng/api';
import { definePreset } from '@primeuix/themes';
import { SlickTranslationLoader } from './core/services/slick-translation-loader.service';

const themePreset = definePreset(Aura, {
  semantic: {
    primary: {
      50: '{cyan.50}',
      100: '{cyan.100}',
      200: '{cyan.200}',
      300: '{cyan.300}',
      400: '{cyan.400}',
      500: '{cyan.500}',
      600: '{cyan.600}',
      700: '{cyan.700}',
      800: '{cyan.800}',
      900: '{cyan.900}',
      950: '{cyan.950}',
    },
  },
});

export const appConfig: ApplicationConfig = {
  providers: [
    provideBrowserGlobalErrorListeners(),
    provideZonelessChangeDetection(),
    provideRouter(routes),
    provideHttpClient(withInterceptors([authInterceptor])),
    provideAnimations(),
    provideTranslateService({
      loader: provideTranslateLoader(SlickTranslationLoader),
      fallbackLang: 'en',
      lang: navigator.language,
    }),
    {
      provide: LOCALE_ID,
      useFactory: () => {
        const locale = navigator.language || 'en-US';
        return locale;
      },
    },
    providePrimeNG({
      theme: {
        preset: themePreset,
      },
    }),
    provideAppInitializer(() => localeInitializer()),
    MessageService,
  ],
};
