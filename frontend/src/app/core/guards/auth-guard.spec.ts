import { TestBed } from '@angular/core/testing';
import { Router } from '@angular/router';
import { Observable, of, throwError } from 'rxjs';
import { authGuard } from './auth-guard';
import { AuthApiService } from 'src/app/features/auth/auth-api.service';
import { provideZonelessChangeDetection } from '@angular/core';

describe('authGuard', () => {
  let authApiServiceMock: jasmine.SpyObj<AuthApiService>;
  let routerMock: jasmine.SpyObj<Router>;

  beforeEach(() => {
    authApiServiceMock = jasmine.createSpyObj('AuthApiService', ['isAuthorized']);
    routerMock = jasmine.createSpyObj('Router', ['navigate']);

    TestBed.configureTestingModule({
      providers: [
        provideZonelessChangeDetection(),
        { provide: AuthApiService, useValue: authApiServiceMock },
        { provide: Router, useValue: routerMock },
      ],
    });
  });

  function runGuard() {
    return TestBed.runInInjectionContext(() => authGuard({} as any, {} as any) as Observable<any>);
  }

  it('should return true when user is authorized', (done) => {
    authApiServiceMock.isAuthorized.and.returnValue(of(null));

    runGuard().subscribe((result) => {
      expect(result).toBeTrue();
      expect(routerMock.navigate).not.toHaveBeenCalled();
      done();
    });
  });

  it('should return false and redirect when unauthorized (error)', (done) => {
    authApiServiceMock.isAuthorized.and.returnValue(throwError(() => new Error('Unauthorized')));

    runGuard().subscribe((result) => {
      expect(result).toBeFalse();
      expect(routerMock.navigate).toHaveBeenCalledWith(['/auth']);
      done();
    });
  });
});
