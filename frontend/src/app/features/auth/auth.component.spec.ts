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

describe('AuthComponent', () => {
  let component: AuthComponent;
  let fixture: ComponentFixture<AuthComponent>;
  let de: DebugElement;

  let authApiServiceMock: jasmine.SpyObj<AuthApiService>;
  let routerMock: jasmine.SpyObj<Router>;
  let toastServiceMock: jasmine.SpyObj<ToastService>;

  beforeEach(async () => {
    authApiServiceMock = jasmine.createSpyObj('AuthApiService', ['initiateLogin'], {
      isDisabled: jasmine.createSpy('isDisabled').and.returnValue(of(false)),
      isPasswordSet: jasmine.createSpy('isPasswordSet').and.returnValue(of(true)),
      isAuthProviderEnabled: jasmine.createSpy('isAuthProviderEnabled').and.returnValue(of(true)),
      setPassword: jasmine.createSpy('setPassword').and.returnValue(of({})),
      login: jasmine.createSpy('login').and.returnValue(of({})),
    });
    routerMock = jasmine.createSpyObj('Router', ['navigate']);
    toastServiceMock = jasmine.createSpyObj('ToastService', ['success', 'error']);

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
    authApiServiceMock.isDisabled.and.returnValue(of(true));
    fixture.detectChanges();
    await fixture.whenStable();
    expect(routerMock.navigate).toHaveBeenCalledWith(['/containers']);
  });

  it('should not navigate if auth enabled', async () => {
    authApiServiceMock.isDisabled.and.returnValue(of(false));
    fixture.detectChanges();
    await fixture.whenStable();
    expect(routerMock.navigate).not.toHaveBeenCalled();
  });

  it('should display new password form if not set', async () => {
    authApiServiceMock.isPasswordSet.and.returnValue(of(false));
    fixture.detectChanges();
    await fixture.whenStable();
    const newPasswordForm = de.query(By.directive(NewPasswordFormComponent));
    expect(newPasswordForm).toBeTruthy();
  });

  it('should display oidc button if enabled', async () => {
    authApiServiceMock.isAuthProviderEnabled.and.callFake((provider) =>
      provider == 'oidc' ? of(true) : of(false),
    );
    fixture.detectChanges();
    await fixture.whenStable();
    const oidcButton = de.query(By.css('.oidc-only-login'));
    expect(oidcButton).toBeTruthy();
  });

  it('should display auth form if enabled', async () => {
    authApiServiceMock.isAuthProviderEnabled.and.callFake((provider) =>
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
    expect(routerMock.navigate).toHaveBeenCalledOnceWith(['/containers']);
  });

  it('should not navigate after failure login', async () => {
    authApiServiceMock.login.and.returnValue(throwError(() => new Error('test')));
    fixture.detectChanges();
    await fixture.whenStable();
    component['onSubmitLogin']('test');
    expect(routerMock.navigate).not.toHaveBeenCalled();
    expect(toastServiceMock.error).toHaveBeenCalledTimes(1);
  });
});
