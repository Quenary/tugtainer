import {
  HttpErrorResponse,
  HttpInterceptorFn,
  HttpRequest,
} from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import {
  Observable,
  catchError,
  finalize,
  switchMap,
  throwError,
  timeout,
  shareReplay,
  of,
} from 'rxjs';
import { AuthApiService } from 'src/app/features/auth/auth-api.service';

const isIgnored = (req: HttpRequest<unknown>): boolean => {
  return /^[^?#]*\/(?:login|refresh)\/?(?:[?#].*)?$/.test(req.url);
};

const isRefreshable = (req: HttpRequest<unknown>, error: unknown): boolean => {
  return (
    error instanceof HttpErrorResponse &&
    error.status === 401 &&
    !isIgnored(req)
  );
};

let refresh$: Observable<unknown> | null = null;

let loggingOut = false;

const shouldLogout = (req: HttpRequest<unknown>, error: unknown): boolean => {
  return !loggingOut && isRefreshable(req, error);
};

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authApiService = inject(AuthApiService);
  const router = inject(Router);

  return next(req).pipe(
    catchError((error) => {
      if (!isRefreshable(req, error)) {
        return throwError(() => error);
      }

      if (!refresh$) {
        refresh$ = authApiService.refresh().pipe(
          timeout(10_000),
          catchError(() => of(null)),
          finalize(() => (refresh$ = null)),
          shareReplay(1),
        );
      }

      return refresh$.pipe(
        switchMap(() =>
          next(req.clone()).pipe(
            catchError((error) => {
              if (shouldLogout(req, error)) {
                loggingOut = true;
                router.navigate(['/auth']).finally(() => (loggingOut = false));
              }

              return throwError(() => error);
            }),
          ),
        ),
      );
    }),
  );
};
