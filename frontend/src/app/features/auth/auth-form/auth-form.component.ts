import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { FormGroup, FormControl, Validators, ReactiveFormsModule } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { ERegexp } from 'src/app/app.consts';
import { ButtonModule } from 'primeng/button';
import { PasswordModule } from 'primeng/password';
import { IftaLabelModule } from 'primeng/iftalabel';
import { AutoFocusModule } from 'primeng/autofocus';

@Component({
  selector: 'app-auth-form',
  imports: [
    TranslatePipe,
    ReactiveFormsModule,
    ButtonModule,
    PasswordModule,
    IftaLabelModule,
    AutoFocusModule,
  ],
  templateUrl: './auth-form.component.html',
  styleUrl: './auth-form.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class AuthFormComponent {
  public readonly isLoading = input<boolean>(false);
  public readonly OnSubmit = output<string>();

  protected readonly form = new FormGroup({
    password: new FormControl<string>(null, [
      Validators.required,
      Validators.pattern(ERegexp.password),
    ]),
  });

  protected onSubmit(): void {
    if (this.form.invalid) {
      return;
    }
    this.form.markAsPristine();
    this.OnSubmit.emit(this.form.value.password);
  }
}
