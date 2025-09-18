import { Component, input, output, signal } from '@angular/core';
import {
  AbstractControl,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import { MatButton } from '@angular/material/button';
import { MatFormField, MatLabel, MatSuffix } from '@angular/material/form-field';
import { MatIcon } from '@angular/material/icon';
import { MatInput } from '@angular/material/input';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';
import { ERegexp } from 'src/app/app.consts';
import { ISetPasswordBody } from 'src/app/entities/auth/auth-interface';
import { TInterfaceToForm } from 'src/app/shared/types/interface-to-form.type';

@Component({
  selector: 'app-new-password-form',
  imports: [
    TranslateModule,
    ReactiveFormsModule,
    MatButton,
    MatFormField,
    MatInput,
    MatLabel,
    MatIcon,
    MatSuffix,
    MatProgressSpinner,
  ],
  templateUrl: './new-password-form.html',
  styleUrl: './new-password-form.scss',
})
export class NewPasswordForm {
  public readonly isLoading = input<boolean>(false);
  public readonly OnSubmit = output<ISetPasswordBody>();

  private readonly passwordMatchValidator = (
    field1 = 'password',
    field2 = 'confirm_password'
  ): ValidatorFn => {
    return (control: AbstractControl) => {
      const form = control as FormGroup;
      const value1 = form.controls[field1].value;
      const value2 = form.controls[field2].value;
      if (value1 != value2) {
        return { passwordMatchValidator: true };
      }
      return null;
    };
  };

  public readonly form = new FormGroup<TInterfaceToForm<ISetPasswordBody>>(
    {
      password: new FormControl<string>(null, [
        Validators.required,
        Validators.pattern(ERegexp.password),
      ]),
      confirm_password: new FormControl<string>(null, [
        Validators.required,
        Validators.pattern(ERegexp.password),
      ]),
    },
    this.passwordMatchValidator()
  );

  public readonly hidePassword = signal(true);
  public readonly hideConfirmPassword = signal(true);

  public onSubmit(): void {
    if (this.form.invalid) {
      return;
    }
    this.OnSubmit.emit(this.form.getRawValue());
  }
}
