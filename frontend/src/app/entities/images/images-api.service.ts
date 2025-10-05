import { Injectable } from '@angular/core';
import { BaseApiService } from '../base/base-api.service';
import { Observable } from 'rxjs';
import { IImage, IImagePruneResult } from './images-interface';

@Injectable({
  providedIn: 'root',
})
export class ImagesApiService extends BaseApiService<'/images'> {
  protected override readonly prefix = '/images';

  list(): Observable<IImage[]> {
    return this.httpClient.get<IImage[]>(`${this.basePath}/list`);
  }

  prune(): Observable<IImagePruneResult> {
    return this.httpClient.post<IImagePruneResult>(`${this.basePath}/prune`, {});
  }
}
