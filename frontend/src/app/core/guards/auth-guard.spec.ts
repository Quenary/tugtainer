import { TestBed } from '@angular/core/testing';
import {
  ActivatedRouteSnapshot,
  Router,
  RouterStateSnapshot,
} from '@angular/router';
import { firstValueFrom, Observable, of, throwError } from 'rxjs';
import { authGuard } from './auth-guard';
import { AuthApiService } from 'src/app/features/auth/auth-api.service';
import { provideZonelessChangeDetection } from '@angular/core';
import { Mocked } from 'vitest';
import { getAuthApiServiceMock } from '@testing/mocks/auth-api.service.mock';

describe('authGuard', () => {
  let authApiServiceMock: Mocked<AuthApiService>;
  let routerMock: Partial<Mocked<Router>>;

  beforeEach(() => {
    authApiServiceMock = getAuthApiServiceMock();
    routerMock = {
      navigate: vi.fn(),
    };

    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        { provide: AuthApiService, useValue: authApiServiceMock },
        { provide: Router, useValue: routerMock },
      ],
    });
  });

  function runGuard() {
    return TestBed.runInInjectionContext(
      () =>
        authGuard(
          {} as ActivatedRouteSnapshot,
          {} as RouterStateSnapshot,
        ) as Observable<boolean>,
    );
  }

  it('should return true when user is authorized', async () => {
    authApiServiceMock.isAuthorized.mockReturnValue(of(null));

    const result = await firstValueFrom(runGuard());

    expect(result).toBe(true);
    expect(routerMock.navigate).not.toHaveBeenCalled();
  });

  it('should return false and redirect when unauthorized (error)', async () => {
    authApiServiceMock.isAuthorized.mockReturnValue(
      throwError(() => new Error('Unauthorized')),
    );

    const result = await firstValueFrom(runGuard());

    expect(result).toBe(false);
    expect(routerMock.navigate).toHaveBeenCalledWith(['/auth']);
  });
});
