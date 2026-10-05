import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { TranslateLoader, TranslationObject } from '@ngx-translate/core';
import {
  catchError,
  map,
  Observable,
  of,
  shareReplay,
  switchMap,
  throwError,
} from 'rxjs';
import { defaultLang } from 'src/app/app.consts';
import { PublicApiService } from 'src/app/features/public/public-api.service';
import { parse } from 'yaml';

@Injectable()
export class SlickTranslationLoader implements TranslateLoader {
  protected readonly publicApiService = inject(PublicApiService);
  protected readonly httpClient = inject(HttpClient);
  protected readonly version$ = this.publicApiService.getVersion().pipe(
    map((res) => res?.image_version?.trim() || null),
    catchError(() => of(null)),
    shareReplay(),
  );

  getTranslation(lang: string): Observable<TranslationObject> {
    return this.version$.pipe(
      switchMap((version) =>
        this.loadYaml(`i18n/${lang}.yaml`, version).pipe(
          catchError(() =>
            this.loadYaml(`i18n/${lang.split('-')[0]}.yaml`, version),
          ),
          // Last resort: never leave the app without translation
          catchError((err) =>
            lang === defaultLang
              ? throwError(() => err)
              : this.loadYaml(`i18n/${defaultLang}.yaml`, version),
          ),
        ),
      ),
    );
  }

  private loadYaml(
    path: string,
    version: string | null,
  ): Observable<TranslationObject> {
    return this.httpClient
      .get(path, {
        params: version ? { version } : {},
        responseType: 'text',
      })
      .pipe(map((data) => parse(data)));
  }
}
