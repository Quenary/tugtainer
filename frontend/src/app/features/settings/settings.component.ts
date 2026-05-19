import {
  ChangeDetectionStrategy,
  Component,
  inject,
  linkedSignal,
} from '@angular/core';
import { NewPasswordFormComponent } from '@shared/components/new-password-form/new-password-form.component';
import { SettingsFormComponent } from './settings-form/settings-form.component';
import { ISetPasswordBody } from 'src/app/features/auth/auth.interface';
import { TranslatePipe } from '@ngx-translate/core';
import { AuthApiService } from 'src/app/features/auth/auth-api.service';
import { finalize } from 'rxjs';
import { DividerModule } from 'primeng/divider';
import { AccordionModule } from 'primeng/accordion';
import { ToastService } from 'src/app/core/services/toast.service';
import { SettingsStore } from './settings.store';

@Component({
  selector: 'app-settings',
  imports: [
    NewPasswordFormComponent,
    TranslatePipe,
    SettingsFormComponent,
    DividerModule,
    AccordionModule,
  ],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SettingsComponent {
  private readonly toastService = inject(ToastService);
  private readonly authApiService = inject(AuthApiService);
  protected readonly settingsStore = inject(SettingsStore);

  public readonly isLoading = linkedSignal(() => this.settingsStore.loading());

  public onSubmitNewPassword(body: ISetPasswordBody): void {
    this.isLoading.set(true);
    this.authApiService
      .setPassword(body)
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
