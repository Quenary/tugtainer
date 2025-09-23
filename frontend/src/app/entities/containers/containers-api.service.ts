import { Injectable } from '@angular/core';
import { BaseApiService } from '../base/base-api.service';
import { Observable } from 'rxjs';
import { ICheckProgress, IContainer, IContainerPatchBody } from './containers-interface';

@Injectable({
  providedIn: 'root',
})
export class ContainersApiService extends BaseApiService<'containers'> {
  protected override readonly prefix: 'containers' = 'containers';

  list(): Observable<IContainer[]> {
    return this.httpClient.get<IContainer[]>(`${this.basePath}/list`);
  }

  patch(name: string, body: IContainerPatchBody): Observable<IContainer> {
    return this.httpClient.patch<IContainer>(`${this.basePath}/${name}`, body);
  }

  checkAndUpdate(): Observable<string> {
    return this.httpClient.post<string>(`${this.basePath}/check_and_update`, {});
  }

  getCheckProgress(id: string): Observable<ICheckProgress> {
    return this.httpClient.get<ICheckProgress>(`${this.basePath}/check_progress/${id}`);
  }
}
