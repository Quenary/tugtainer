import { Injectable } from '@angular/core';
import { BaseApiService } from '../base/base-api.service';
import { Observable } from 'rxjs';
import { ICreateHost, IHostInfo, IHostStatus } from './hosts-interface';

@Injectable({
  providedIn: 'root',
})
export class HostsApiService extends BaseApiService<'/hosts'> {
  protected override readonly prefix = '/hosts';

  list(): Observable<IHostInfo[]> {
    return this.httpClient.get<IHostInfo[]>(`${this.basePath}/list`);
  }

  create(body: ICreateHost): Observable<IHostInfo> {
    return this.httpClient.post<IHostInfo>(`${this.basePath}`, body);
  }

  read(id: number): Observable<IHostInfo> {
    return this.httpClient.get<IHostInfo>(`${this.basePath}/${id}`);
  }

  update(id: number, body: ICreateHost): Observable<IHostInfo> {
    return this.httpClient.put<IHostInfo>(`${this.basePath}/${id}`, body);
  }

  delete(id: number): Observable<{ detail: string }> {
    return this.httpClient.delete<{ detail: string }>(`${this.basePath}/${id}`);
  }

  status(id: number): Observable<IHostStatus> {
    return this.httpClient.get<IHostStatus>(`${this.basePath}/${id}/status`);
  }
}
