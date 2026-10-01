import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AuthComponent } from './auth.component';
import { AuthApiService } from './auth-api.service';
import { Router } from '@angular/router';
import { ToastService } from 'src/app/core/services/toast.service';
import { DebugElement, provideZonelessChangeDetection } from '@angular/core';
import { provideTranslateService } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';
import { By } from '@angular/platform-browser';
import { AuthRegisterComponent } from './auth-register/auth-register.component';
import { AuthFormComponent } from './auth-form/auth-form.component';
import { Mocked } from 'vitest';
import { getToastServiceMock } from '@testing/mocks/toast-service.mock';
import { getAuthApiServiceMock } from '@testing/mocks/auth-api.service.mock';

describe('AuthComponent', () => {
  let component: AuthComponent;
  let fixture: ComponentFixture<AuthComponent>;
  let de: DebugElement;

  let authApiServiceMock: Mocked<AuthApiService>;
  let routerMock: Partial<Mocked<Router>>;
  let toastServiceMock: Mocked<ToastService>;

  beforeEach(async () => {
    authApiServiceMock = getAuthApiServiceMock();
    authApiServiceMock.isDisabled.mockReturnValue(of(false));
    authApiServiceMock.isPasswordSet.mockReturnValue(of(true));
    authApiServiceMock.isAuthProviderEnabled.mockReturnValue(of(true));
    authApiServiceMock.setPassword.mockReturnValue(of({}));
    authApiServiceMock.login.mockReturnValue(of({}));

    routerMock = {
      navigate: vi.fn(),
    };
    toastServiceMock = getToastServiceMock();

    await TestBed.configureTestingModule({
      imports: [AuthComponent],
      providers: [
        provideZonelessChangeDetection(),
        { provide: AuthApiService, useValue: authApiServiceMock },
        { provide: Router, useValue: routerMock },
        { provide: ToastService, useValue: toastServiceMock },
        provideTranslateService(),
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AuthComponent);
    component = fixture.componentInstance;
    de = fixture.debugElement;
  });

  it('should create', () => {
    fixture.detectChanges();
    expect(component).toBeTruthy();
  });

  describe('availability', () => {
    it('navigates home when auth is disabled', async () => {
      authApiServiceMock.isDisabled.mockReturnValue(of(true));
      fixture.detectChanges();
      await fixture.whenStable();
      expect(routerMock.navigate).toHaveBeenCalledWith(['/']);
    });

    it('stays when auth is enabled', async () => {
      authApiServiceMock.isDisabled.mockReturnValue(of(false));
      fixture.detectChanges();
      await fixture.whenStable();
      expect(routerMock.navigate).not.toHaveBeenCalled();
    });
  });

  describe('visible form', () => {
    it('shows registration when the password is not set', async () => {
      authApiServiceMock.isPasswordSet.mockReturnValue(of(false));
      fixture.detectChanges();
      await fixture.whenStable();
      const registerForm = de.query(By.directive(AuthRegisterComponent));
      expect(registerForm).toBeTruthy();
    });

    it('shows the OIDC button when OIDC is enabled', async () => {
      authApiServiceMock.isAuthProviderEnabled.mockImplementation((provider) =>
        provider == 'oidc' ? of(true) : of(false),
      );
      fixture.detectChanges();
      await fixture.whenStable();
      const oidcButton = de.query(By.css('.oidc-button'));
      expect(oidcButton).toBeTruthy();
    });

    it('shows the password form when password auth is enabled', async () => {
      authApiServiceMock.isAuthProviderEnabled.mockImplementation((provider) =>
        provider == 'password' ? of(true) : of(false),
      );
      fixture.detectChanges();
      await fixture.whenStable();
      const newPasswordForm = de.query(By.directive(AuthFormComponent));
      expect(newPasswordForm).toBeTruthy();
    });
  });

  describe('login', () => {
    it('navigates home after success', async () => {
      fixture.detectChanges();
      await fixture.whenStable();
      component['onSubmitLogin']('test');

      expect(routerMock.navigate).toHaveBeenCalledWith(['/']);
      expect(routerMock.navigate).toHaveBeenCalledTimes(1);
    });

    it('stays and shows an error after failure', async () => {
      authApiServiceMock.login.mockReturnValue(
        throwError(() => new Error('test')),
      );
      fixture.detectChanges();
      await fixture.whenStable();
      component['onSubmitLogin']('test');
      expect(routerMock.navigate).not.toHaveBeenCalled();
      expect(toastServiceMock.error).toHaveBeenCalledTimes(1);
    });
  });
});
