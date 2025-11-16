import { Injectable } from '@angular/core';
import { BaseApiService } from '../base/base-api.service';
import { Observable } from 'rxjs';
import {
  IAllCheckData,
  IHostCheckData,
  IContainerCheckData,
  IContainer,
  IContainerPatchBody,
} from './containers-interface';

@Injectable({
  providedIn: 'root',
})
export class ContainersApiService extends BaseApiService<'/containers'> {
  protected override readonly prefix = '/containers';

  list(host_id: number): Observable<IContainer[]> {
    return this.httpClient.get<IContainer[]>(`${this.basePath}/${host_id}/list`);
  }

  patch(host_id: number, name: string, body: IContainerPatchBody): Observable<IContainer> {
    return this.httpClient.patch<IContainer>(`${this.basePath}/${host_id}/${name}`, body);
  }

  checkAll(update: boolean = false): Observable<string> {
    return this.httpClient.post<string>(`${this.basePath}/check`, {}, { params: { update } });
  }

  checkHost(host_id: number, update: boolean = false): Observable<string> {
    return this.httpClient.post<string>(
      `${this.basePath}/check/${host_id}`,
      {},
      { params: { update } },
    );
  }

  checkContainer(host_id: number, name: string, update: boolean = false): Observable<string> {
    return this.httpClient.post<string>(
      `${this.basePath}/check/${host_id}/${name}`,
      {},
      { params: { update } },
    );
  }

  progress<T extends IContainerCheckData>(cache_id: string): Observable<T> {
    return this.httpClient.get<T>(`${this.basePath}/progress`, { params: { cache_id } });
  }

  isUpdateAvailableSelf(): Observable<boolean> {
    return this.httpClient.get<boolean>(`${this.basePath}/update_available/self`);
  }
}
