import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { catchError, map, of, tap } from 'rxjs';
import { AuthApiService } from 'src/app/features/auth/auth-api.service';

export const authGuard: CanActivateFn = () => {
  const authApiService = inject(AuthApiService);
  const router = inject(Router);

  return authApiService.isAuthorized().pipe(
    map(() => true),
    catchError(() => of(false)),
    tap((res) => {
      if (!res) {
        router.navigate(['/auth']);
      }
    }),
  );
};
