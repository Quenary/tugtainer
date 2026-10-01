import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { provideTranslateService } from '@ngx-translate/core';
import { of, throwError } from 'rxjs';
import { Mocked } from 'vitest';
import { ToastService } from 'src/app/core/services/toast.service';
import { AuthApiService } from 'src/app/features/auth/auth-api.service';
import { getAuthApiServiceMock } from '@testing/mocks/auth-api.service.mock';
import { getToastServiceMock } from '@testing/mocks/toast-service.mock';
import { AuthRegisterComponent } from './auth-register.component';

describe('AuthRegisterComponent', () => {
  let component: AuthRegisterComponent;
  let fixture: ComponentFixture<AuthRegisterComponent>;
  let authApiServiceMock: Mocked<AuthApiService>;
  let toastServiceMock: Mocked<ToastService>;

  beforeEach(async () => {
    authApiServiceMock = getAuthApiServiceMock();
    authApiServiceMock.setPassword.mockReturnValue(of({}));
    toastServiceMock = getToastServiceMock();

    await TestBed.configureTestingModule({
      imports: [AuthRegisterComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideTranslateService(),
        { provide: AuthApiService, useValue: authApiServiceMock },
        { provide: ToastService, useValue: toastServiceMock },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(AuthRegisterComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  function fillForm(): void {
    component['form'].setValue({
      setup_code: 'setup-code',
      password: '123QWErty!',
      confirm_password: '123QWErty!',
    });
    component['form'].markAsDirty();
  }

  it('should not submit an invalid form', () => {
    component['onSubmit']();

    expect(authApiServiceMock.setPassword).not.toHaveBeenCalled();
  });

  it('should send the setup code with the password', () => {
    fillForm();
    component['onSubmit']();

    expect(authApiServiceMock.setPassword).toHaveBeenCalledWith({
      password: '123QWErty!',
      confirm_password: '123QWErty!',
      setup_code: 'setup-code',
    });
  });

  it('should notify the parent after a successful registration', () => {
    const registered = vi.fn();
    component.OnRegistered.subscribe(registered);
    fillForm();
    component['onSubmit']();

    expect(registered).toHaveBeenCalledTimes(1);
    expect(toastServiceMock.success).toHaveBeenCalledTimes(1);
  });

  it('should show an error when registration fails', () => {
    authApiServiceMock.setPassword.mockReturnValue(
      throwError(() => new Error('expired')),
    );
    const registered = vi.fn();
    component.OnRegistered.subscribe(registered);
    fillForm();
    component['onSubmit']();

    expect(registered).not.toHaveBeenCalled();
    expect(toastServiceMock.error).toHaveBeenCalledTimes(1);
  });
});
