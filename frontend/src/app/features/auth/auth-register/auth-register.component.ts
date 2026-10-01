import {
  ChangeDetectionStrategy,
  Component,
  inject,
  output,
  signal,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import {
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { PasswordFieldComponent } from '@shared/components/password-field/password-field.component';
import {
  createPasswordControls,
  passwordMatchValidator,
} from '@shared/forms/password-form';
import { AutoFocusModule } from '@openng/optimus-ui/autofocus';
import { ButtonModule } from '@openng/optimus-ui/button';
import { IftaLabelModule } from '@openng/optimus-ui/iftalabel';
import { InputTextModule } from '@openng/optimus-ui/inputtext';
import { finalize, map } from 'rxjs';
import { ToastService } from 'src/app/core/services/toast.service';
import { AuthApiService } from 'src/app/features/auth/auth-api.service';

@Component({
  selector: 'app-auth-register',
  imports: [
    TranslatePipe,
    ReactiveFormsModule,
    PasswordFieldComponent,
    ButtonModule,
    IftaLabelModule,
    InputTextModule,
    AutoFocusModule,
  ],
  templateUrl: './auth-register.component.html',
  styleUrl: './auth-register.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthRegisterComponent {
  private readonly authApiService = inject(AuthApiService);
  private readonly toastService = inject(ToastService);

  public readonly OnRegistered = output<void>();

  protected readonly isLoading = signal(false);
  protected readonly form = new FormGroup(
    {
      ...createPasswordControls(),
      setup_code: new FormControl<string>(null, [Validators.required]),
    },
    passwordMatchValidator(),
  );

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
        setup_code: value.setup_code,
      })
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: () => {
          this.toastService.success();
          this.OnRegistered.emit();
        },
        error: (error) => {
          this.toastService.error(error);
        },
      });
  }
}
