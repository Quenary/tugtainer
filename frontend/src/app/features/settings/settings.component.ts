import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NewPasswordFormComponent } from '@shared/components/new-password-form/new-password-form.component';
import { SettingsFormComponent } from './settings-form/settings-form.component';
import { ISetPasswordBody } from 'src/app/features/auth/auth.interface';
import { TranslatePipe } from '@ngx-translate/core';
import { AuthApiService } from 'src/app/features/auth/auth-api.service';
import { SettingsApiService } from 'src/app/features/settings/settings-api.service';
import { finalize } from 'rxjs';
import { ISettingUpdate } from 'src/app/features/settings/settings.interface';
import { DividerModule } from 'primeng/divider';
import { AccordionModule } from 'primeng/accordion';
import { ToastService } from 'src/app/core/services/toast.service';

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
  private readonly settingsApiService = inject(SettingsApiService);

  public readonly isLoading = signal<boolean>(false);

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

  public onSubmitSettings(body: ISettingUpdate[]): void {
    this.isLoading.set(true);
    this.settingsApiService
      .change(body)
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
