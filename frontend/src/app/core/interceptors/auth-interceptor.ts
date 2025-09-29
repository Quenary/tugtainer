import { HttpErrorResponse, HttpInterceptorFn, HttpRequest } from '@angular/common/http';
import { inject } from '@angular/core';
import { Router } from '@angular/router';
import { BehaviorSubject, catchError, first, of, switchMap, tap, throwError, timeout } from 'rxjs';
import { AuthApiService } from 'src/app/entities/auth/auth-api.service';

const ignoreList = ['/login', '/refresh'];

const ignore = (req: HttpRequest<unknown>): boolean => {
  return ignoreList.some((item) => req.url.includes(item));
};

const isRefreshable = (req: HttpRequest<unknown>, error: unknown): boolean => {
  return error instanceof HttpErrorResponse && error.status === 401 && req && !ignore(req);
};

const isRefreshing$ = new BehaviorSubject<boolean>(false);

export const authInterceptor: HttpInterceptorFn = (req, next) => {
  const authApiService = inject(AuthApiService);
  const router = inject(Router);

  return next(req).pipe(
    catchError((error) => {
      if (isRefreshable(req, error)) {
        if (!isRefreshing$.getValue()) {
          isRefreshing$.next(true);
          authApiService
            .refresh()
            .pipe(
              catchError(() => of(null)),
              tap(() => isRefreshing$.next(false)),
            )
            .subscribe();
        }

        return isRefreshing$.pipe(
          first((flag) => !flag),
          timeout(10000),
          catchError(() => of(null)),
          switchMap(() => {
            return next(req.clone()).pipe(
              catchError((error) => {
                if (isRefreshable(req, error)) {
                  router.navigate(['/auth']);
                }
                return throwError(() => error);
              }),
            );
          }),
        );
      }

      return throwError(() => error);
    }),
  );
};
