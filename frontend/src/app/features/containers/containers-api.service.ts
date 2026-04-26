import { Injectable } from '@angular/core';
import { BaseApiService } from '../../shared/types/base-api.service';
import { Observable, repeat, takeWhile } from 'rxjs';
import {
  IContainerListItem,
  IContainerPatchBody,
  IContainerInfo,
  TControlContainerCommand,
  IGetContainerLogsRequestBody,
} from './containers.interface';
import {
  EActionStatus,
  IActionProgress,
} from '../../shared/interfaces/progress.interface';

@Injectable({
  providedIn: 'root',
})
export class ContainersApiService extends BaseApiService<'/containers'> {
  protected override readonly prefix = '/containers';

  list(host_id: number): Observable<IContainerListItem[]> {
    return this.httpClient.get<IContainerListItem[]>(
      `${this.basePath}/${host_id}/list`,
    );
  }

  get(hostId: number, containerNameOrId: string): Observable<IContainerInfo> {
    return this.httpClient.get<IContainerInfo>(
      `${this.basePath}/${hostId}/${containerNameOrId}`,
    );
  }

  patch(
    host_id: number,
    name: string,
    body: IContainerPatchBody,
  ): Observable<IContainerListItem> {
    return this.httpClient.patch<IContainerListItem>(
      `${this.basePath}/${host_id}/${name}`,
      body,
    );
  }

  checkAll(): Observable<string> {
    return this.httpClient.post<string>(`${this.basePath}/check`, {});
  }

  checkHost(host_id: number): Observable<string> {
    return this.httpClient.post<string>(
      `${this.basePath}/check/${host_id}`,
      {},
    );
  }

  checkContainer(host_id: number, name: string): Observable<string> {
    return this.httpClient.post<string>(
      `${this.basePath}/check/${host_id}/${name}`,
      {},
    );
  }

  updateAll(): Observable<string> {
    return this.httpClient.post<string>(`${this.basePath}/update`, {});
  }

  updateHost(host_id: number): Observable<string> {
    return this.httpClient.post<string>(
      `${this.basePath}/update/${host_id}`,
      {},
    );
  }

  updateContainer(host_id: number, name: string): Observable<string> {
    return this.httpClient.post<string>(
      `${this.basePath}/update/${host_id}/${name}`,
      {},
    );
  }

  /**
   * Get progress
   * @param cache_id id of progress cache
   * @returns
   */
  progress<T extends IActionProgress>(cache_id: string): Observable<T> {
    return this.httpClient.get<T>(`${this.basePath}/progress`, {
      params: { cache_id },
    });
  }

  /**
   * Watch progress, emits until status not DONE or ERROR
   * @param cache_id id of progress cache
   * @returns
   */
  watchProgress<T extends IActionProgress>(cache_id: string): Observable<T> {
    return this.progress<T>(cache_id).pipe(
      repeat({ delay: 500 }),
      takeWhile(
        (res) =>
          ![EActionStatus.DONE, EActionStatus.ERROR].includes(res?.status),
        true,
      ),
    );
  }

  /**
   * Control container state with basic commands
   * @param hostId
   * @param command
   * @param containerNameOrId
   * @returns
   */
  controlContainer(
    hostId: number,
    command: TControlContainerCommand,
    containerNameOrId: string,
  ): Observable<IContainerInfo> {
    return this.httpClient.post<IContainerInfo>(
      `${this.basePath}/${hostId}/${command}/${containerNameOrId}`,
      {},
    );
  }

  logs(
    hostId: number,
    containerNameOrId: string,
    body: IGetContainerLogsRequestBody,
  ): Observable<string> {
    return this.httpClient.post<string>(
      `${this.basePath}/${hostId}/logs/${containerNameOrId}`,
      body,
    );
  }
}
