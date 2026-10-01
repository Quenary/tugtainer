import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { FormControl, ReactiveFormsModule } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { AutoFocusModule } from '@openng/optimus-ui/autofocus';
import { Divider } from '@openng/optimus-ui/divider';
import { IftaLabelModule } from '@openng/optimus-ui/iftalabel';
import { PasswordModule } from '@openng/optimus-ui/password';

@Component({
  selector: 'app-password-field',
  imports: [
    TranslatePipe,
    ReactiveFormsModule,
    PasswordModule,
    IftaLabelModule,
    Divider,
    AutoFocusModule,
  ],
  templateUrl: './password-field.component.html',
  styleUrl: './password-field.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class PasswordFieldComponent {
  public readonly control = input.required<FormControl<string>>();
  public readonly inputId = input.required<string>();
  public readonly labelKey = input.required<string>();
  public readonly autocomplete = input<string>('new-password');
  public readonly autoFocus = input<boolean>(false);
  public readonly invalid = input<boolean>(false);
}
