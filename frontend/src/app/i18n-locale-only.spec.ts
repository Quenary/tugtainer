import { Injectable } from '@angular/core';
import { TestBed } from '@angular/core/testing';
import {
  provideTranslateLoader,
  provideTranslateService,
  TranslateLoader,
  TranslateService,
  TranslationObject,
} from '@ngx-translate/core';
import {
  firstValueFrom,
  Observable,
  of,
  switchMap,
  throwError,
  timer,
} from 'rxjs';
import { resolveTranslationLang } from './core/services/locale.service';

/** Loader that only knows the catalogs shipped in public/i18n. */
@Injectable()
class OnlyShippedCatalogsLoader implements TranslateLoader {
  getTranslation(lang: string): Observable<TranslationObject> {
    return timer(0).pipe(
      switchMap(() =>
        ['en', 'ru', 'zh', 'ko'].includes(lang)
          ? of({ BREADCRUMBS: { HOSTS: `Hosts (${lang})` } })
          : throwError(() => new Error(`404 i18n/${lang}.yaml`)),
      ),
    );
  }
}

const setup = (lang: string) => {
  vi.spyOn(console, 'warn').mockImplementation(() => undefined);
  TestBed.configureTestingModule({
    providers: [
      provideTranslateService({
        loader: provideTranslateLoader(OnlyShippedCatalogsLoader),
        fallbackLang: 'en',
        lang,
      }),
    ],
  });
  return TestBed.inject(TranslateService);
};

describe('locale-only languages (#255)', () => {
  it('ngx-translate v18: stream() errors when the initial lang has no catalog', async () => {
    const ts = setup('de');
    await expect(firstValueFrom(ts.stream('BREADCRUMBS'))).rejects.toThrow(
      '404 i18n/de.yaml',
    );
  });

  it('with resolveTranslationLang the stream emits English', async () => {
    const ts = setup(resolveTranslationLang('de'));
    await expect(firstValueFrom(ts.stream('BREADCRUMBS'))).resolves.toEqual({
      HOSTS: 'Hosts (en)',
    });
  });
});
