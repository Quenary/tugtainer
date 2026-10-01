import { ChangeDetectionStrategy, Component } from '@angular/core';
import { SettingsChangePasswordComponent } from './settings-change-password/settings-change-password.component';
import { SettingsFormComponent } from './settings-form/settings-form.component';
import { TranslatePipe } from '@ngx-translate/core';
import { DividerModule } from '@openng/optimus-ui/divider';
import { AccordionModule } from '@openng/optimus-ui/accordion';

@Component({
  selector: 'app-settings',
  imports: [
    SettingsChangePasswordComponent,
    TranslatePipe,
    SettingsFormComponent,
    DividerModule,
    AccordionModule,
  ],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SettingsComponent {}
