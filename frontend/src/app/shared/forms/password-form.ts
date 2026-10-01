import {
  AbstractControl,
  FormControl,
  FormGroup,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import { ERegexp } from 'src/app/app.consts';

export interface PasswordControls {
  password: FormControl<string>;
  confirm_password: FormControl<string>;
}

export function passwordMatchValidator(
  field1 = 'password',
  field2 = 'confirm_password',
): ValidatorFn {
  return (control: AbstractControl) => {
    const form = control as FormGroup;
    const value1 = form.controls[field1].value;
    const value2 = form.controls[field2].value;
    if (value1 != value2) {
      return { passwordMatchValidator: true };
    }
    return null;
  };
}

export function createPasswordControls(): PasswordControls {
  return {
    password: new FormControl<string>(null, [
      Validators.required,
      Validators.pattern(ERegexp.password),
    ]),
    confirm_password: new FormControl<string>(null, [
      Validators.required,
      Validators.pattern(ERegexp.password),
    ]),
  };
}

export function createPasswordForm(): FormGroup<PasswordControls> {
  return new FormGroup(createPasswordControls(), passwordMatchValidator());
}
