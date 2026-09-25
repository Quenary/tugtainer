import { Injectable } from '@angular/core';
import { Observable } from 'rxjs';
import { BaseApiService } from '@shared/types/base-api.service';
import { IServiceListItem, IServicePatchBody } from './services.interface';

@Injectable({
  providedIn: 'root',
})
export class ServicesApiService extends BaseApiService<'/hosts'> {
  protected override readonly prefix = '/hosts';

  list(hostId: number): Observable<IServiceListItem[]> {
    return this.httpClient.get<IServiceListItem[]>(
      `${this.basePath}/${hostId}/services`,
    );
  }

  patch(
    hostId: number,
    serviceName: string,
    body: IServicePatchBody,
  ): Observable<IServiceListItem> {
    return this.httpClient.patch<IServiceListItem>(
      `${this.basePath}/${hostId}/services/${serviceName}`,
      body,
    );
  }

  check(hostId: number, names?: string[]): Observable<{ detail: string }> {
    return this.httpClient.post<{ detail: string }>(
      `${this.basePath}/${hostId}/services/check`,
      names?.length ? { names } : {},
    );
  }

  update(hostId: number, names?: string[]): Observable<{ detail: string }> {
    return this.httpClient.post<{ detail: string }>(
      `${this.basePath}/${hostId}/services/update`,
      names?.length ? { names } : {},
    );
  }

  logs(
    hostId: number,
    serviceName: string,
    tail = 100,
    timestamps = false,
  ): Observable<string> {
    return this.httpClient.get(
      `${this.basePath}/${hostId}/services/${serviceName}/logs`,
      {
        params: {
          tail,
          timestamps,
        },
        responseType: 'text',
      },
    );
  }
}
