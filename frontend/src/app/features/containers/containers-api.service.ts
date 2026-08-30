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
  EJobStatus,
  IAllHostsState,
  IHostState,
} from '../../shared/interfaces/jobs.interface';

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

  hooksEnabled(): Observable<boolean> {
    return this.httpClient.get<boolean>(`${this.basePath}/hooks_enabled`);
  }

  checkAll(): Observable<string> {
    return this.httpClient.post<string>(`${this.basePath}/check`, {});
  }

  checkHost(host_id: number, names?: string[]): Observable<string> {
    return this.httpClient.post<string>(
      `${this.basePath}/check/${host_id}`,
      names?.length ? { names } : {},
    );
  }

  checkContainer(host_id: number, name: string): Observable<string> {
    return this.checkHost(host_id, [name]);
  }

  updateAll(): Observable<string> {
    return this.httpClient.post<string>(`${this.basePath}/update`, {});
  }

  updateHost(host_id: number, names?: string[]): Observable<string> {
    return this.httpClient.post<string>(
      `${this.basePath}/update/${host_id}`,
      names?.length ? { names } : {},
    );
  }

  updateContainer(host_id: number, name: string): Observable<string> {
    return this.updateHost(host_id, [name]);
  }

  /**
   * Unified per-host job state
   */
  hostState(host_id: number): Observable<IHostState | null> {
    return this.httpClient.get<IHostState | null>(
      `${this.basePath}/progress/${host_id}`,
    );
  }

  /**
   * Get job state by cache id
   */
  jobState<T extends IHostState | IAllHostsState>(
    cache_id: string,
  ): Observable<T> {
    return this.httpClient.get<T>(`${this.basePath}/progress`, {
      params: { cache_id },
    });
  }

  /**
   * Watch job state until DONE or ERROR
   */
  watchJobState<T extends IHostState | IAllHostsState>(
    cache_id: string,
  ): Observable<T> {
    return this.jobState<T>(cache_id).pipe(
      repeat({ delay: 500 }),
      takeWhile(
        (res) =>
          res && ![EJobStatus.DONE, EJobStatus.ERROR].includes(res.status),
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
