import { ComponentFixture, TestBed } from '@angular/core/testing';
import { provideZonelessChangeDetection } from '@angular/core';
import { provideTranslateService } from '@ngx-translate/core';
import { of } from 'rxjs';
import { Mocked } from 'vitest';
import { ToastService } from 'src/app/core/services/toast.service';
import { AuthApiService } from 'src/app/features/auth/auth-api.service';
import { getAuthApiServiceMock } from '@testing/mocks/auth-api.service.mock';
import { getToastServiceMock } from '@testing/mocks/toast-service.mock';
import { SettingsChangePasswordComponent } from './settings-change-password.component';

describe('SettingsChangePasswordComponent', () => {
  let component: SettingsChangePasswordComponent;
  let fixture: ComponentFixture<SettingsChangePasswordComponent>;
  let authApiServiceMock: Mocked<AuthApiService>;

  beforeEach(async () => {
    authApiServiceMock = getAuthApiServiceMock();
    authApiServiceMock.setPassword.mockReturnValue(of({}));

    await TestBed.configureTestingModule({
      imports: [SettingsChangePasswordComponent],
      providers: [
        provideZonelessChangeDetection(),
        provideTranslateService(),
        { provide: AuthApiService, useValue: authApiServiceMock },
        { provide: ToastService, useValue: getToastServiceMock() },
      ],
    }).compileComponents();

    fixture = TestBed.createComponent(SettingsChangePasswordComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should send a password change without a setup code', () => {
    component['form'].setValue({
      password: '123QWErty!',
      confirm_password: '123QWErty!',
    });
    component['form'].markAsDirty();
    component['onSubmit']();

    expect(authApiServiceMock.setPassword).toHaveBeenCalledWith({
      password: '123QWErty!',
      confirm_password: '123QWErty!',
    });
    expect(authApiServiceMock.setPassword.mock.calls[0][0]).not.toHaveProperty(
      'setup_code',
    );
  });
});
