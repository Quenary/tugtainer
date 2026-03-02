import { HttpClient } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { environment } from '@env/environment';

type TypeOfBasePath<P extends string> = P extends '' ? '/api' : `/api${P}`;

/**
 * Base service for all api services
 */
@Injectable()
export abstract class BaseApiService<Prefix extends string = null> {
  /**
   * Http client
   */
  protected readonly httpClient = inject(HttpClient);
  /**
   * Prefix for the api router.
   */
  protected readonly prefix: Prefix = null;
  /**
   * Base path for the api service.
   *
   * Combines {@link environment.api} and {@link prefix}.
   */
  protected get basePath(): TypeOfBasePath<Prefix> {
    const api = environment.api as '/api';
    if (typeof this.prefix !== 'string') {
      return api as TypeOfBasePath<Prefix>;
    }
    return `${api}${this.prefix}` as TypeOfBasePath<Prefix>;
  }
}
