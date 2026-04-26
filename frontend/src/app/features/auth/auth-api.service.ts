import { Injectable } from '@angular/core';
import { BaseApiService } from '../../shared/types/base-api.service';
import { Observable } from 'rxjs';
import { ISetPasswordBody, TAuthProvider } from './auth.interface';

@Injectable({
  providedIn: 'root',
})
export class AuthApiService extends BaseApiService<'/auth'> {
  protected override readonly prefix = '/auth';

  isDisabled(): Observable<boolean> {
    return this.httpClient.get<boolean>(`${this.basePath}/is_disabled`);
  }

  /**
   * Check if auth provider enabled
   * @param provider provider code
   * @returns
   */
  isAuthProviderEnabled(provider: TAuthProvider): Observable<boolean> {
    return this.httpClient.get<boolean>(`${this.basePath}/${provider}/enabled`);
  }

  /**
   * Auth with active auth provider
   * @param provider
   * @param body
   * @param params
   * @returns
   */
  login(
    provider: TAuthProvider,
    body: Record<string, unknown> = {},
    params: Record<string, string> = {},
  ): Observable<unknown> {
    return this.httpClient.post(`${this.basePath}/${provider}/login`, body, {
      params,
      withCredentials: true,
    });
  }

  /**
   * Login with redirection to provider
   * @param provider
   */
  initiateLogin(provider: TAuthProvider): void {
    window.location.href = `${this.basePath}/${provider}/login`;
  }

  refresh(): Observable<unknown> {
    return this.httpClient.post(
      `${this.basePath}/refresh`,
      {},
      { withCredentials: true },
    );
  }

  logout(): Observable<unknown> {
    return this.httpClient.post(
      `${this.basePath}/logout`,
      {},
      { withCredentials: true },
    );
  }

  setPassword(body: ISetPasswordBody): Observable<unknown> {
    return this.httpClient.post(`${this.basePath}/set_password`, body, {
      withCredentials: true,
    });
  }

  isAuthorized(): Observable<null> {
    return this.httpClient.get<null>(`${this.basePath}/is_authorized`, {
      withCredentials: true,
    });
  }

  isPasswordSet(): Observable<boolean> {
    return this.httpClient.get<boolean>(`${this.basePath}/is_password_set`);
  }
}
