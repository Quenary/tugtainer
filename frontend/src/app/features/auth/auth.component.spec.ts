import { ComponentFixture, TestBed } from '@angular/core/testing';
import { AuthComponent } from './auth.component';
import { AuthApiService } from './auth-api.service';
import { Router } from '@angular/router';
import { ToastService } from 'src/app/core/services/toast.service';
import { DebugElement, provideZonelessChangeDetection } from '@angular/core';
import { provideTranslateService } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';
import { By } from '@angular/platform-browser';
import { NewPasswordFormComponent } from '@shared/components/new-password-form/new-password-form.component';
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

  it('should navigate if auth disabled', async () => {
    authApiServiceMock.isDisabled.mockReturnValue(of(true));
    fixture.detectChanges();
    await fixture.whenStable();
    expect(routerMock.navigate).toHaveBeenCalledWith(['/']);
  });

  it('should not navigate if auth enabled', async () => {
    authApiServiceMock.isDisabled.mockReturnValue(of(false));
    fixture.detectChanges();
    await fixture.whenStable();
    expect(routerMock.navigate).not.toHaveBeenCalled();
  });

  it('should display new password form if not set', async () => {
    authApiServiceMock.isPasswordSet.mockReturnValue(of(false));
    fixture.detectChanges();
    await fixture.whenStable();
    const newPasswordForm = de.query(By.directive(NewPasswordFormComponent));
    expect(newPasswordForm).toBeTruthy();
  });

  it('should display oidc button if enabled', async () => {
    authApiServiceMock.isAuthProviderEnabled.mockImplementation((provider) =>
      provider == 'oidc' ? of(true) : of(false),
    );
    fixture.detectChanges();
    await fixture.whenStable();
    const oidcButton = de.query(By.css('.oidc-button'));
    expect(oidcButton).toBeTruthy();
  });

  it('should display auth form if enabled', async () => {
    authApiServiceMock.isAuthProviderEnabled.mockImplementation((provider) =>
      provider == 'password' ? of(true) : of(false),
    );
    fixture.detectChanges();
    await fixture.whenStable();
    const newPasswordForm = de.query(By.directive(AuthFormComponent));
    expect(newPasswordForm).toBeTruthy();
  });

  it('should navigate after success login', async () => {
    fixture.detectChanges();
    await fixture.whenStable();
    component['onSubmitLogin']('test');

    expect(routerMock.navigate).toHaveBeenCalledWith(['/']);
    expect(routerMock.navigate).toHaveBeenCalledTimes(1);
  });

  it('should not navigate after failure login', async () => {
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
