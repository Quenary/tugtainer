import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ReactiveFormsModule } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { PasswordFieldComponent } from '@shared/components/password-field/password-field.component';
import { createPasswordForm } from '@shared/forms/password-form';
import { ButtonModule } from '@openng/optimus-ui/button';
import { finalize, map } from 'rxjs';
import { ToastService } from 'src/app/core/services/toast.service';
import { AuthApiService } from 'src/app/features/auth/auth-api.service';

@Component({
  selector: 'app-settings-change-password',
  imports: [
    TranslatePipe,
    ReactiveFormsModule,
    PasswordFieldComponent,
    ButtonModule,
  ],
  templateUrl: './settings-change-password.component.html',
  styleUrl: './settings-change-password.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SettingsChangePasswordComponent {
  private readonly authApiService = inject(AuthApiService);
  private readonly toastService = inject(ToastService);

  protected readonly isLoading = signal(false);
  protected readonly form = createPasswordForm();

  protected readonly confirmPasswordError = toSignal(
    this.form.valueChanges.pipe(
      map(() => !!this.form.errors?.['passwordMatchValidator']),
    ),
  );

  protected onSubmit(): void {
    if (this.form.invalid) {
      return;
    }
    this.form.markAsPristine();
    const value = this.form.getRawValue();
    this.isLoading.set(true);
    this.authApiService
      .setPassword({
        password: value.password,
        confirm_password: value.confirm_password,
      })
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: () => {
          this.toastService.success();
        },
        error: (error) => {
          this.toastService.error(error);
        },
      });
  }
}
