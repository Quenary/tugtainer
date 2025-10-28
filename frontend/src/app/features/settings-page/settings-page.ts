import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NewPasswordForm } from 'src/app/shared/components/new-password-form/new-password-form';
import { SettingsPageForm } from './settings-page-form/settings-page-form';
import { ISetPasswordBody } from 'src/app/entities/auth/auth-interface';
import { TranslatePipe } from '@ngx-translate/core';
import { AuthApiService } from 'src/app/entities/auth/auth-api.service';
import { SettingsApiService } from 'src/app/entities/settings/settings-api.service';
import { finalize } from 'rxjs';
import { ISettingUpdate, ESettingKey } from 'src/app/entities/settings/settings-interface';
import { DividerModule } from 'primeng/divider';
import { AccordionModule } from 'primeng/accordion';
import { MessageModule } from 'primeng/message';
import { ToastService } from 'src/app/core/services/toast.service';

@Component({
  selector: 'app-settings-page',
  imports: [NewPasswordForm, TranslatePipe, SettingsPageForm, DividerModule, AccordionModule, MessageModule],
  templateUrl: './settings-page.html',
  styleUrl: './settings-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SettingsPage {
  private readonly toastService = inject(ToastService);
  private readonly authApiService = inject(AuthApiService);
  private readonly settingsApiService = inject(SettingsApiService);

  public readonly isLoading = signal<boolean>(false);
  
  public readonly oidcSettingKeys = [
    ESettingKey.OIDC_ENABLED,
    ESettingKey.OIDC_WELL_KNOWN_URL,
    ESettingKey.OIDC_CLIENT_ID,
    ESettingKey.OIDC_CLIENT_SECRET,
    ESettingKey.OIDC_REDIRECT_URI,
    ESettingKey.OIDC_SCOPES
  ];

  public get currentUrl(): string {
    return window.location.origin;
  }

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
