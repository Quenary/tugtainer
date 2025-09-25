import { Injectable } from '@angular/core';
import { BaseApiService } from '../base/base-api.service';
import { Observable } from 'rxjs';
import { IVersion } from './public-interface';

@Injectable({
  providedIn: 'root',
})
export class PublicApiService extends BaseApiService<'/public'> {
  protected override readonly prefix = '/public';

  public getVersion(): Observable<IVersion> {
    return this.httpClient.get<IVersion>(`${this.basePath}/version`);
  }

  public getHealth(): Observable<'OK'> {
    return this.httpClient.get<'OK'>(`${this.basePath}/health`);
  }
}
