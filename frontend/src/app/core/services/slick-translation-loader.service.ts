import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { TranslateLoader } from '@ngx-translate/core';
import { catchError, map, Observable, of, shareReplay, switchMap, tap } from 'rxjs';
import { PublicApiService } from 'src/app/entities/public/public-api.service';

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
    let version: string = null;
    return this.version$.pipe(
      tap((res) => (version = res)),
      switchMap(() => this.httpClient.get(`i18n/${lang}.json`, { params: { version } })),
      catchError(() => {
        return this.httpClient.get(`i18n/${lang.split('-')[0]}.json`, { params: { version } });
      }),
    );
  }
}
