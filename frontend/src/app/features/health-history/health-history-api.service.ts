import { Injectable } from '@angular/core';
import { BaseApiService } from '../../shared/types/base-api.service';
import { Observable } from 'rxjs';
import {
  IHealthHistoryFilterRequest,
  IHealthHistoryPagedResponse,
} from './health-history.interface';

@Injectable({
  providedIn: 'root',
})
export class HealthHistoryApiService extends BaseApiService<'/health'> {
  protected override readonly prefix = '/health';

  getHistory(
    req: IHealthHistoryFilterRequest,
  ): Observable<IHealthHistoryPagedResponse> {
    return this.httpClient.post<IHealthHistoryPagedResponse>(
      `${this.basePath}/history`,
      req,
    );
  }
}
