import { Injectable } from '@angular/core';
import { TranslateLoader } from '@ngx-translate/core';
import { Observable } from 'rxjs';

@Injectable()
export class DynamicImportTranslationLoader implements TranslateLoader {
  getTranslation(lang: string): Observable<any> {
    return new Observable((observer) => {
      import(`../../../../public/i18n/${lang}.json`)
        .then((res) => {
          observer.next(res.default);
        })
        .catch(() => {
          observer.next(null);
        })
        .finally(() => {
          observer.complete();
        });
    });
  }
}
