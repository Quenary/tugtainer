import { Component, inject, output, signal } from '@angular/core';
import {
  AbstractControl,
  FormArray,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { MessageService } from 'primeng/api';
import { finalize } from 'rxjs';
import { SettingsApiService } from 'src/app/entities/settings/settings-api.service';
import {
  ESettingKey,
  ESettingValueType,
  ISetting,
  ISettingUpdate,
} from 'src/app/entities/settings/settings-interface';
import { parseError } from 'src/app/shared/functions/parse-error.function';
import { TInterfaceToForm } from 'src/app/shared/types/interface-to-form.type';
import cronValidate from 'cron-validate';
import { ButtonModule } from 'primeng/button';
import { IftaLabelModule } from 'primeng/iftalabel';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { DividerModule } from 'primeng/divider';
import { ToggleSwitchModule } from 'primeng/toggleswitch';
import { TooltipModule } from 'primeng/tooltip';
import { FluidModule } from 'primeng/fluid';

@Component({
  selector: 'app-settings-form',
  imports: [
    ReactiveFormsModule,
    ButtonModule,
    IftaLabelModule,
    InputTextModule,
    InputNumberModule,
    DividerModule,
    ToggleSwitchModule,
    TranslateModule,
    TooltipModule,
    FluidModule,
  ],
  templateUrl: './settings-form.html',
  styleUrl: './settings-form.scss',
})
export class SettingsForm {
  private readonly settingsApiService = inject(SettingsApiService);
  private readonly translateService = inject(TranslateService);
  private readonly messageService = inject(MessageService);

  public readonly OnSubmit = output<ISettingUpdate[]>();

  public readonly ESettingKey = ESettingKey;
  public readonly keyTranslates = this.translateService.instant('SETTINGS.BY_KEY');
  public readonly isLoading = signal<boolean>(false);
  public readonly formArray = new FormArray<FormGroup<TInterfaceToForm<ISetting>>>([]);

  private cronValidator: ValidatorFn = (control: AbstractControl<string>) => {
    const value = control.value;
    if (!!value) {
      const cv = cronValidate(value);
      return cv.isValid() ? null : { cronValidator: true };
    }
    return null;
  };

  constructor() {
    this.updateSettings();
  }

  private updateSettings(): void {
    this.isLoading.set(true);
    this.settingsApiService
      .list()
      .pipe(
        finalize(() => {
          this.isLoading.set(false);
        }),
      )
      .subscribe({
        next: (list) => {
          this.formArray.clear();
          for (const item of list) {
            const form = this.getFormGroup(item);
            this.formArray.push(form);
          }
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

  private getFormGroup(data: ISetting): FormGroup<TInterfaceToForm<ISetting>> {
    const form = new FormGroup<TInterfaceToForm<ISetting>>({
      key: new FormControl<ESettingKey>(data.key),
      value: new FormControl<any>(data.value, [Validators.required]),
      value_type: new FormControl<ESettingValueType>(data.value_type),
      updated_at: new FormControl<string>({ value: data.updated_at, disabled: true }),
    });

    if (data.key === ESettingKey.CRONTAB_EXPR) {
      form.controls.value.addValidators([this.cronValidator]);
    }

    return form;
  }

  public onHintClick(link: string): void {
    if (link) {
      window.open(link, '_blank');
    }
  }

  public onTestNotification(): void {
    this.isLoading.set(true);
    this.settingsApiService
      .test_notification()
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next:() => {
          this.messageService.add({
            severity:'success',
            summary: this.translateService.instant('GENERAL.SUCCESS'),
          })
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

  public submit(): void {
    if (this.formArray.invalid) {
      return;
    }
    this.formArray.markAsPristine();
    const value = this.formArray.getRawValue().map((item) => ({
      key: item.key,
      value: item.value,
    }));
    this.OnSubmit.emit(value);
  }
}
