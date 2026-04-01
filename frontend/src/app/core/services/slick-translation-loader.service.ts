import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { TranslateLoader } from '@ngx-translate/core';
import {
  catchError,
  map,
  Observable,
  of,
  shareReplay,
  switchMap,
  tap,
} from 'rxjs';
import { PublicApiService } from 'src/app/features/public/public-api.service';
import { parse } from 'yaml';

@Injectable()
export class SlickTranslationLoader implements TranslateLoader {
  protected readonly publicApiService = inject(PublicApiService);
  protected readonly httpClient = inject(HttpClient);
  protected readonly version$ = this.publicApiService.getVersion().pipe(
    map((res) => res?.image_version),
    catchError(() => of(null)),
    shareReplay(),
  );

  getTranslation(lang: string): Observable<any> {
    let version: string | null = null;
    return this.version$.pipe(
      tap((res) => {
        version = res;
      }),
      switchMap(() =>
        this.httpClient.get(`i18n/${lang}.yaml`, {
          params: { version },
          responseType: 'text',
        }),
      ),
      catchError(() =>
        this.httpClient.get(`i18n/${lang.split('-')[0]}.yaml`, {
          params: { version },
          responseType: 'text',
        }),
      ),
      map((data) => parse(data)),
    );
  }
}
