import { Injectable } from '@angular/core';
import { BaseApiService } from '../../shared/types/base-api.service';
import { Observable } from 'rxjs';
import {
  ISelfUpdateState,
  ISelfUpdateStatusResponse,
} from './self-update.interface';

@Injectable({
  providedIn: 'root',
})
export class SelfUpdateApiService extends BaseApiService<'/self_update'> {
  protected override readonly prefix = '/self_update';

  getStatus(): Observable<ISelfUpdateStatusResponse> {
    return this.httpClient.get<ISelfUpdateStatusResponse>(
      `${this.basePath}/status`,
    );
  }

  start(): Observable<ISelfUpdateState> {
    return this.httpClient.post<ISelfUpdateState>(
      `${this.basePath}/start`,
      null,
    );
  }
}
