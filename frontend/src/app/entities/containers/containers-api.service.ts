import { Injectable } from '@angular/core';
import { BaseApiService } from '../base/base-api.service';
import { Observable, repeat, takeWhile } from 'rxjs';
import { IContainerListItem, IContainerPatchBody, IContainerInfo } from './containers-interface';
import { ECheckStatus, IBaseCheckProgressCache } from '../progress-cache/progress-cache.interface';

@Injectable({
  providedIn: 'root',
})
export class ContainersApiService extends BaseApiService<'/containers'> {
  protected override readonly prefix = '/containers';

  list(host_id: number): Observable<IContainerListItem[]> {
    return this.httpClient.get<IContainerListItem[]>(`${this.basePath}/${host_id}/list`);
  }

  get(hostId: number, containerNameOrId: string): Observable<IContainerInfo> {
    return this.httpClient.get<IContainerInfo>(`${this.basePath}/${hostId}/${containerNameOrId}`);
  }

  patch(host_id: number, name: string, body: IContainerPatchBody): Observable<IContainerListItem> {
    return this.httpClient.patch<IContainerListItem>(`${this.basePath}/${host_id}/${name}`, body);
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

  /**
   * Get progress
   * @param cache_id id of progress cache
   * @returns
   */
  progress<T extends IBaseCheckProgressCache>(cache_id: string): Observable<T> {
    return this.httpClient.get<T>(`${this.basePath}/progress`, { params: { cache_id } });
  }

  /**
   * Watch progress, emits until status not DONE or ERROR
   * @param cache_id id of progress cache
   * @returns
   */
  watchProgress<T extends IBaseCheckProgressCache>(cache_id: string): Observable<T> {
    return this.progress<T>(cache_id).pipe(
      repeat({ delay: 500 }),
      takeWhile((res) => ![ECheckStatus.DONE, ECheckStatus.ERROR].includes(res?.status), true),
    );
  }
}
