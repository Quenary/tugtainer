import { TestBed } from '@angular/core/testing';
import {
  HttpClient,
  HttpErrorResponse,
  provideHttpClient,
  withInterceptors,
} from '@angular/common/http';
import {
  provideHttpClientTesting,
  HttpTestingController,
} from '@angular/common/http/testing';
import { provideRouter, Router } from '@angular/router';
import { Subject, timer } from 'rxjs';
import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { AuthApiService } from 'src/app/features/auth/auth-api.service';
import { authInterceptor } from './auth-interceptor';

let http: HttpClient;
let httpMock: HttpTestingController;
let router: Router;
let authApiServiceMock: { refresh: ReturnType<typeof vi.fn> };
let refreshSubject: Subject<unknown>;

describe('authInterceptor', () => {
  beforeEach(() => {
    TestBed.resetTestingModule();

    authApiServiceMock = { refresh: vi.fn() };
    refreshSubject = new Subject<unknown>();
    authApiServiceMock.refresh.mockReturnValue(refreshSubject.asObservable());

    TestBed.configureTestingModule({
      providers: [
        provideHttpClient(withInterceptors([authInterceptor])),
        provideHttpClientTesting(),
        provideRouter([]),
        { provide: AuthApiService, useValue: authApiServiceMock },
      ],
    });

    http = TestBed.inject(HttpClient);
    httpMock = TestBed.inject(HttpTestingController);
    router = TestBed.inject(Router);
    vi.spyOn(router, 'navigate').mockResolvedValue(true);
  });

  afterEach(() => {
    vi.useRealTimers();
    httpMock.verify();
  });

  describe('requests that skip refresh', () => {
    it('passes a successful request through', () => {
      const result = vi.fn();
      const error = vi.fn();

      http.get('/api/data').subscribe({ next: result, error });
      httpMock.expectOne('/api/data').flush({ data: 'ok' });

      expect(result).toHaveBeenCalledWith({ data: 'ok' });
      expect(error).not.toHaveBeenCalled();
      expect(authApiServiceMock.refresh).not.toHaveBeenCalled();
      expect(router.navigate).not.toHaveBeenCalled();
    });

    it('rethrows a non-401 error', () => {
      const result = vi.fn();

      http.get('/api/data').subscribe({ error: result });
      httpMock
        .expectOne('/api/data')
        .flush(null, { status: 500, statusText: 'Server Error' });

      expect(result).toHaveBeenCalledWith(
        expect.objectContaining({ status: 500 }),
      );
      expect(authApiServiceMock.refresh).not.toHaveBeenCalled();
      expect(router.navigate).not.toHaveBeenCalled();
    });
  });

  describe('ignored auth urls', () => {
    it.each([
      ['/login match 1', '/api/auth/password/login'],
      ['/login match 2', '/api/auth/oidc/login'],
      ['/refresh match', '/api/auth/refresh'],
      ['/refresh match with query params', '/api/auth/refresh?force=1'],
    ])('rethrows a 401 from %s', (_label, url) => {
      const result = vi.fn();

      http.get(url).subscribe({ error: result });
      httpMock
        .expectOne(url)
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      expect(result).toHaveBeenCalledWith(
        expect.objectContaining({ status: 401 }),
      );
      expect(authApiServiceMock.refresh).not.toHaveBeenCalled();
      expect(router.navigate).not.toHaveBeenCalled();
    });

    it.each([
      ['path contains an ignored word', '/api/logins/stats'],
      ['query string contains an ignored word', '/api/orders?redirect=/login'],
    ])('still refreshes when the %s', (_label, url) => {
      const result = vi.fn();

      http.get(url).subscribe({ next: result, error: vi.fn() });
      httpMock
        .expectOne(url)
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      expect(authApiServiceMock.refresh).toHaveBeenCalledTimes(1);

      refreshSubject.next({ token: 'new' });
      refreshSubject.complete();

      httpMock.expectOne(url).flush({ data: 'ok' });
      expect(result).toHaveBeenCalledWith({ data: 'ok' });
      expect(router.navigate).not.toHaveBeenCalled();
    });
  });

  describe('refresh', () => {
    it('retries the request after success', () => {
      const result = vi.fn();
      const error = vi.fn();

      http.get('/api/data').subscribe({ next: result, error });

      const original = httpMock.expectOne('/api/data');
      const originalReq = original.request;
      original.flush(null, { status: 401, statusText: 'Unauthorized' });

      expect(authApiServiceMock.refresh).toHaveBeenCalledTimes(1);

      refreshSubject.next({ token: 'new' });
      refreshSubject.complete();

      const retry = httpMock.expectOne('/api/data');
      expect(retry.request).not.toBe(originalReq);
      retry.flush({ data: 'ok' });

      expect(result).toHaveBeenCalledWith({ data: 'ok' });
      expect(error).not.toHaveBeenCalled();
      expect(router.navigate).not.toHaveBeenCalled();
    });

    it('shares one refresh across concurrent and late 401s', () => {
      const s1 = vi.fn();
      const s2 = vi.fn();
      const s3 = vi.fn();

      http.get('/api/a').subscribe({ next: s1, error: vi.fn() });
      http.get('/api/b').subscribe({ next: s2, error: vi.fn() });

      httpMock
        .expectOne('/api/a')
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      http.get('/api/c').subscribe({ next: s3, error: vi.fn() });

      httpMock
        .expectOne('/api/b')
        .flush(null, { status: 401, statusText: 'Unauthorized' });
      httpMock
        .expectOne('/api/c')
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      expect(authApiServiceMock.refresh).toHaveBeenCalledTimes(1);

      refreshSubject.next({ token: 'new' });
      refreshSubject.complete();

      httpMock.expectOne('/api/a').flush('a');
      httpMock.expectOne('/api/b').flush('b');
      httpMock.expectOne('/api/c').flush('c');

      expect(s1).toHaveBeenCalledWith('a');
      expect(s2).toHaveBeenCalledWith('b');
      expect(s3).toHaveBeenCalledWith('c');
    });

    it('starts a new refresh after the previous one completed', () => {
      const s1 = vi.fn();
      http.get('/api/a').subscribe({ next: s1, error: vi.fn() });
      httpMock
        .expectOne('/api/a')
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      refreshSubject.next({ token: 'new' });
      refreshSubject.complete();
      httpMock.expectOne('/api/a').flush('a');

      expect(authApiServiceMock.refresh).toHaveBeenCalledTimes(1);
      expect(router.navigate).not.toHaveBeenCalled();

      const refreshSubject2 = new Subject<unknown>();
      authApiServiceMock.refresh.mockReturnValue(
        refreshSubject2.asObservable(),
      );

      const s2 = vi.fn();
      http.get('/api/b').subscribe({ next: s2, error: vi.fn() });
      httpMock
        .expectOne('/api/b')
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      expect(authApiServiceMock.refresh).toHaveBeenCalledTimes(2);

      refreshSubject2.next({ token: 'new' });
      refreshSubject2.complete();
      httpMock.expectOne('/api/b').flush('b');

      expect(s2).toHaveBeenCalledWith('b');
      expect(router.navigate).not.toHaveBeenCalled();
    });

    it('starts a new refresh after a failed refresh', () => {
      const err1 = vi.fn();
      http.get('/api/a').subscribe({ error: err1 });
      httpMock
        .expectOne('/api/a')
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      refreshSubject.error(new Error('refresh dead'));

      httpMock
        .expectOne('/api/a')
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      expect(err1).toHaveBeenCalledWith(
        expect.objectContaining({ status: 401 }),
      );
      expect(router.navigate).toHaveBeenCalledTimes(1);

      const refreshSubject2 = new Subject<unknown>();
      authApiServiceMock.refresh.mockReturnValue(
        refreshSubject2.asObservable(),
      );

      const s2 = vi.fn();
      http.get('/api/b').subscribe({ next: s2, error: vi.fn() });
      httpMock
        .expectOne('/api/b')
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      expect(authApiServiceMock.refresh).toHaveBeenCalledTimes(2);
      expect(router.navigate).toHaveBeenCalledTimes(1);

      refreshSubject2.next({ token: 'new' });
      refreshSubject2.complete();
      httpMock.expectOne('/api/b').flush('b');

      expect(s2).toHaveBeenCalledWith('b');
    });
  });

  describe('logout', () => {
    it('logs out when the refresh fails and the retry is 401', () => {
      const result = vi.fn();

      http.get('/api/data').subscribe({ error: result });
      httpMock
        .expectOne('/api/data')
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      expect(authApiServiceMock.refresh).toHaveBeenCalledTimes(1);

      refreshSubject.error(new Error('refresh dead'));

      httpMock
        .expectOne('/api/data')
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      expect(router.navigate).toHaveBeenCalledWith(['/auth']);
      expect(result).toHaveBeenCalledWith(
        expect.objectContaining({ status: 401 }),
      );
    });

    it('does not log out when the retry is not a 401', () => {
      const result = vi.fn();

      http.get('/api/data').subscribe({ error: result });
      httpMock
        .expectOne('/api/data')
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      refreshSubject.next({ token: 'new' });
      refreshSubject.complete();

      httpMock
        .expectOne('/api/data')
        .flush(null, { status: 500, statusText: 'Server Error' });

      expect(router.navigate).not.toHaveBeenCalled();
      expect(result).toHaveBeenCalledWith(
        expect.objectContaining({ status: 500 }),
      );
    });

    it('logs out when the retried request is 401', () => {
      const result = vi.fn();

      http.get('/api/data').subscribe({ error: result });
      httpMock
        .expectOne('/api/data')
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      refreshSubject.next({ token: 'new' });
      refreshSubject.complete();

      httpMock
        .expectOne('/api/data')
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      expect(router.navigate).toHaveBeenCalledWith(['/auth']);
      expect(result).toHaveBeenCalledWith(
        expect.objectContaining({ status: 401 }),
      );
    });

    it('logs out when the refresh times out and the retry is 401', () => {
      vi.useFakeTimers({
        toFake: ['setTimeout', 'clearTimeout', 'setInterval', 'clearInterval'],
      });

      authApiServiceMock.refresh.mockReturnValue(timer(60_000));

      const result = vi.fn();

      http.get('/api/data').subscribe({ error: result });
      httpMock
        .expectOne('/api/data')
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      expect(authApiServiceMock.refresh).toHaveBeenCalledTimes(1);

      vi.advanceTimersByTime(10_001);

      httpMock
        .expectOne('/api/data')
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      expect(router.navigate).toHaveBeenCalledWith(['/auth']);
      expect(result).toHaveBeenCalledWith(
        expect.objectContaining({ status: 401 }),
      );
    });

    it('does not log out when the refresh fails but the retry succeeds', () => {
      const result = vi.fn();
      const error = vi.fn();

      http.get('/api/data').subscribe({ next: result, error });
      httpMock
        .expectOne('/api/data')
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      refreshSubject.error(
        new HttpErrorResponse({ status: 500, statusText: 'Server Error' }),
      );

      httpMock.expectOne('/api/data').flush({ data: 'ok' });

      expect(result).toHaveBeenCalledWith({ data: 'ok' });
      expect(error).not.toHaveBeenCalled();
      expect(router.navigate).not.toHaveBeenCalled();
    });

    it('navigates once when concurrent retries are all 401', () => {
      const e1 = vi.fn();
      const e2 = vi.fn();
      const e3 = vi.fn();

      http.get('/api/a').subscribe({ next: vi.fn(), error: e1 });
      http.get('/api/b').subscribe({ next: vi.fn(), error: e2 });
      http.get('/api/c').subscribe({ next: vi.fn(), error: e3 });

      httpMock
        .expectOne('/api/a')
        .flush(null, { status: 401, statusText: 'Unauthorized' });
      httpMock
        .expectOne('/api/b')
        .flush(null, { status: 401, statusText: 'Unauthorized' });
      httpMock
        .expectOne('/api/c')
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      expect(authApiServiceMock.refresh).toHaveBeenCalledTimes(1);

      refreshSubject.next({ token: 'new' });
      refreshSubject.complete();

      httpMock
        .expectOne('/api/a')
        .flush(null, { status: 401, statusText: 'Unauthorized' });
      httpMock
        .expectOne('/api/b')
        .flush(null, { status: 401, statusText: 'Unauthorized' });
      httpMock
        .expectOne('/api/c')
        .flush(null, { status: 401, statusText: 'Unauthorized' });

      expect(router.navigate).toHaveBeenCalledTimes(1);

      expect(e1).toHaveBeenCalledWith(expect.objectContaining({ status: 401 }));
      expect(e2).toHaveBeenCalledWith(expect.objectContaining({ status: 401 }));
      expect(e3).toHaveBeenCalledWith(expect.objectContaining({ status: 401 }));
    });
  });
});
