import { Injectable } from '@angular/core';
import { BaseApiService } from '../../shared/types/base-api.service';
import { Observable } from 'rxjs';
import {
  IHostSummary,
  IsUpdateAvailableResponseBody,
  IVersion,
} from './public-interface';

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

  public isUpdateAvailable(): Observable<IsUpdateAvailableResponseBody> {
    return this.httpClient.get<IsUpdateAvailableResponseBody>(
      `${this.basePath}/is_update_available`,
    );
  }

  public getSummary(): Observable<IHostSummary[]> {
    return this.httpClient.get<IHostSummary[]>(`${this.basePath}/summary`);
  }
}
