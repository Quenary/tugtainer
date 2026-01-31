import { inject, Injectable } from '@angular/core';
import { BaseApiService } from '../base/base-api.service';
import { Observable, tap } from 'rxjs';
import { ISetting, ISettingUpdate, ITestNotificationRequestBody } from './settings-interface';
import { SettingsService } from './settings.service';

@Injectable({
  providedIn: 'root',
})
export class SettingsApiService extends BaseApiService<'/settings'> {
  protected override readonly prefix = '/settings';
  protected readonly settingsService = inject(SettingsService);

  list(): Observable<ISetting[]> {
    return this.httpClient
      .get<ISetting[]>(`${this.basePath}/list`)
      .pipe(tap((res) => this.settingsService.settings.set(res)));
  }

  change(settings: ISettingUpdate[]): Observable<any> {
    return this.httpClient.patch(`${this.basePath}/change`, settings);
  }

  test_notification(body: ITestNotificationRequestBody): Observable<any> {
    return this.httpClient.post(`${this.basePath}/test_notification`, body);
  }

  getAvailableTimezones(): Observable<string[]> {
    return this.httpClient.get<string[]>(`${this.basePath}/available_timezones`);
  }
}
