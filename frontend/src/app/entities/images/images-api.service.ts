import { Injectable } from '@angular/core';
import { BaseApiService } from '../base/base-api.service';
import { Observable } from 'rxjs';
import { IImage } from './images-interface';

@Injectable({
  providedIn: 'root',
})
export class ImagesApiService extends BaseApiService<'/images'> {
  protected override readonly prefix = '/images';

  list(host_id: number): Observable<IImage[]> {
    return this.httpClient.get<IImage[]>(`${this.basePath}/${host_id}/list`);
  }

  prune(host_id: number): Observable<string> {
    return this.httpClient.post<string>(`${this.basePath}/${host_id}/prune`, {});
  }
}
