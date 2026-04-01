import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { TranslateLoader } from '@ngx-translate/core';
import { catchError, map, Observable, of, shareReplay, switchMap } from 'rxjs';
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
    return this.version$.pipe(
      switchMap((version) =>
        this.loadYaml(`i18n/${lang}.yaml`, version).pipe(
          catchError(() =>
            this.loadYaml(`i18n/${lang.split('-')[0]}.yaml`, version),
          ),
        ),
      ),
    );
  }

  private loadYaml(path: string, version: string): Observable<any> {
    return this.httpClient
      .get(path, {
        params: { version },
        responseType: 'text',
      })
      .pipe(map((data) => parse(data)));
  }
}
