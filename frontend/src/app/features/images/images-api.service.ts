import { Injectable } from '@angular/core';
import { BaseApiService } from '../../shared/types/base-api.service';
import { Observable } from 'rxjs';
import {
  IImage,
  IImageInspectResult,
  IPruneImageRequestBodySchema,
} from './images.interface';

@Injectable({
  providedIn: 'root',
})
export class ImagesApiService extends BaseApiService<'/images'> {
  protected override readonly prefix = '/images';

  list(host_id: number): Observable<IImage[]> {
    return this.httpClient.get<IImage[]>(`${this.basePath}/${host_id}/list`);
  }

  inspect(hostId: number, imageId: string): Observable<IImageInspectResult> {
    return this.httpClient.get<IImageInspectResult>(
      `${this.basePath}/${hostId}/${imageId}`,
    );
  }

  prune(
    host_id: number,
    body: IPruneImageRequestBodySchema,
  ): Observable<string> {
    return this.httpClient.post<string>(
      `${this.basePath}/${host_id}/prune`,
      body,
    );
  }
}
