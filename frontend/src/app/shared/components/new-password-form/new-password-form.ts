import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import {
  AbstractControl,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { ERegexp } from 'src/app/app.consts';
import { ISetPasswordBody } from 'src/app/entities/auth/auth-interface';
import { TInterfaceToForm } from 'src/app/shared/types/interface-to-form.type';
import { ButtonModule } from 'primeng/button';
import { PasswordModule } from 'primeng/password';
import { IftaLabelModule } from 'primeng/iftalabel';
import { Divider } from 'primeng/divider';
import { map } from 'rxjs';

@Component({
  selector: 'app-new-password-form',
  imports: [
    TranslatePipe,
    ReactiveFormsModule,
    ButtonModule,
    PasswordModule,
    IftaLabelModule,
    Divider,
  ],
  templateUrl: './new-password-form.html',
  styleUrl: './new-password-form.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class NewPasswordForm {
  public readonly isLoading = input<boolean>(false);
  public readonly fluidButton = input<boolean>(false);
  public readonly OnSubmit = output<ISetPasswordBody>();

  private readonly passwordMatchValidator = (
    field1 = 'password',
    field2 = 'confirm_password',
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
    this.passwordMatchValidator(),
  );

  public readonly confirmPasswordError = toSignal(
    this.form.valueChanges.pipe(map(() => !!this.form.errors?.['passwordMatchValidator'])),
  );

  public onSubmit(): void {
    if (this.form.invalid) {
      return;
    }
    this.form.markAsPristine();
    this.OnSubmit.emit(this.form.getRawValue());
  }
}
