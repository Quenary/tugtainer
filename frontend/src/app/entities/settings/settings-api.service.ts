import { Injectable } from '@angular/core';
import { BaseApiService } from '../base/base-api.service';
import { Observable } from 'rxjs';
import { ISetting, ISettingUpdate } from './settings-interface';

@Injectable({
  providedIn: 'root',
})
export class SettingsApiService extends BaseApiService<'/settings'> {
  protected override readonly prefix = '/settings';

  list(): Observable<ISetting[]> {
    return this.httpClient.get<ISetting[]>(`${this.basePath}/list`);
  }

  change(settings: ISettingUpdate[]): Observable<any> {
    return this.httpClient.patch(`${this.basePath}/change`, settings);
  }

  test_notification(url: string): Observable<any> {
    return this.httpClient.post(`${this.basePath}/test_notification`, { url });
  }

  getAvailableTimezones(): Observable<string[]> {
    return this.httpClient.get<string[]>(`${this.basePath}/available_timezones`);
  }

  testOidcConnection(well_known_url: string): Observable<any> {
    return this.httpClient.post(`${this.basePath}/test_oidc`, { well_known_url });
  }
}
