import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { NewPasswordForm } from 'src/app/shared/components/new-password-form/new-password-form';
import { SettingsForm } from './settings-form/settings-form';
import { ISetPasswordBody } from 'src/app/entities/auth/auth-interface';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { MessageService } from 'primeng/api';
import { AuthApiService } from 'src/app/entities/auth/auth-api.service';
import { SettingsApiService } from 'src/app/entities/settings/settings-api.service';
import { finalize } from 'rxjs';
import { parseError } from 'src/app/shared/functions/parse-error.function';
import { ISettingUpdate } from 'src/app/entities/settings/settings-interface';
import { DividerModule } from 'primeng/divider';
import { AccordionModule } from 'primeng/accordion';

@Component({
  selector: 'app-settings-page',
  imports: [NewPasswordForm, SettingsForm, DividerModule, TranslateModule, AccordionModule],
  templateUrl: './settings-page.html',
  styleUrl: './settings-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SettingsPage {
  private readonly translateService = inject(TranslateService);
  private readonly messageService = inject(MessageService);
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
          this.messageService.add({
            severity: 'success',
            summary: this.translateService.instant('GENERAL.SUCCESS'),
          });
        },
        error: (error) => {
          this.messageService.add({
            severity: 'error',
            summary: this.translateService.instant('GENERAL.ERROR'),
            detail: parseError(error),
          });
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
          this.messageService.add({
            severity: 'success',
            summary: this.translateService.instant('GENERAL.SUCCESS'),
          });
        },
        error: (error) => {
          this.messageService.add({
            severity: 'error',
            summary: this.translateService.instant('GENERAL.ERROR'),
            detail: parseError(error),
          });
        },
      });
  }
}
