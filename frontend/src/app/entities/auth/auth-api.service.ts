import { Injectable } from '@angular/core';
import { BaseApiService } from '../base/base-api.service';
import { Observable } from 'rxjs';
import { ISetPasswordBody } from './auth-interface';

@Injectable({
  providedIn: 'root',
})
export class AuthApiService extends BaseApiService<'/auth'> {
  protected override readonly prefix = '/auth';

  login(password: string): Observable<any> {
    return this.httpClient.post(
      `${this.basePath}/login`,
      {},
      { params: { password }, withCredentials: true },
    );
  }

  refresh(): Observable<any> {
    return this.httpClient.post(`${this.basePath}/refresh`, {}, { withCredentials: true });
  }

  logout(): Observable<any> {
    return this.httpClient.post(`${this.basePath}/logout`, {}, { withCredentials: true });
  }

  setPassword(body: ISetPasswordBody): Observable<any> {
    return this.httpClient.post(`${this.basePath}/set_password`, body, { withCredentials: true });
  }

  isAuthorized(): Observable<null> {
    return this.httpClient.get<null>(`${this.basePath}/is_authorized`, {
      withCredentials: true,
    });
  }

  isPasswordSet(): Observable<boolean> {
    return this.httpClient.get<boolean>(`${this.basePath}/is_password_set`);
  }

  isOidcEnabled(): Observable<boolean> {
    return this.httpClient.get<boolean>(`${this.basePath}/oidc/enabled`);
  }

  initiateOidcLogin(): Observable<any> {
    // This will redirect to the OIDC provider, so we don't expect a JSON response
    window.location.href = `${this.basePath}/oidc/login`;
    return new Observable(subscriber => {
      // This observable won't emit since we're redirecting
      subscriber.complete();
    });
  }

  getUserInfo(): Observable<any> {
    return this.httpClient.get(`${this.basePath}/user/info`, { withCredentials: true });
  }
}
