import { Injectable } from '@angular/core';
import { BaseApiService } from '../base/base-api.service';
import { Observable } from 'rxjs';
import { ICheckProgress, IContainer, IContainerPatchBody } from './containers-interface';

@Injectable({
  providedIn: 'root',
})
export class ContainersApiService extends BaseApiService<'/containers'> {
  protected override readonly prefix = '/containers';

  list(): Observable<IContainer[]> {
    return this.httpClient.get<IContainer[]>(`${this.basePath}/list`);
  }

  patch(name: string, body: IContainerPatchBody): Observable<IContainer> {
    return this.httpClient.patch<IContainer>(`${this.basePath}/${name}`, body);
  }

  checkAll(): Observable<string> {
    return this.httpClient.post<string>(`${this.basePath}/check/all`, {});
  }

  checkContainer(name: string): Observable<string> {
    return this.httpClient.post<string>(`${this.basePath}/check/${name}`, {});
  }

  updateContainer(name: string): Observable<string> {
    return this.httpClient.post<string>(`${this.basePath}/update/${name}`, {});
  }

  getCheckProgress(id: string): Observable<ICheckProgress> {
    return this.httpClient.get<ICheckProgress>(`${this.basePath}/check_progress/${id}`);
  }

  isUpdateAvailableSelf(): Observable<boolean> {
    return this.httpClient.get<boolean>(`${this.basePath}/update_available/self`);
  }
}
