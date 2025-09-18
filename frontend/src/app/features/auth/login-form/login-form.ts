import { Component, input, output, signal } from '@angular/core';
import { FormGroup, FormControl, Validators, ReactiveFormsModule } from '@angular/forms';
import { MatButton } from '@angular/material/button';
import { MatFormField, MatLabel, MatSuffix } from '@angular/material/form-field';
import { MatIcon } from '@angular/material/icon';
import { MatInput } from '@angular/material/input';
import { MatProgressSpinner } from '@angular/material/progress-spinner';
import { TranslateModule } from '@ngx-translate/core';
import { ERegexp } from 'src/app/app.consts';

@Component({
  selector: 'app-login-form',
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
  templateUrl: './login-form.html',
  styleUrl: './login-form.scss',
})
export class LoginForm {
  public readonly isLoading = input<boolean>(false);
  public readonly OnSubmit = output<string>();

  public readonly form = new FormGroup({
    password: new FormControl<string>(null, [
      Validators.required,
      Validators.pattern(ERegexp.password),
    ]),
  });
  public readonly hidePassword = signal(true);

  public onSubmit(): void {
    if (this.form.invalid) {
      return;
    }
    this.OnSubmit.emit(this.form.value.password);
  }
}
