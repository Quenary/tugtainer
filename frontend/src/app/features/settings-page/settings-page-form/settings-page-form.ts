import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import {
  AbstractControl,
  FormArray,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { catchError, finalize, of } from 'rxjs';
import { SettingsApiService } from 'src/app/entities/settings/settings-api.service';
import { AuthApiService } from 'src/app/entities/auth/auth-api.service';
import {
  ESettingKey,
  ESettingValueType,
  ISetting,
  ISettingUpdate,
} from 'src/app/entities/settings/settings-interface';
import { TInterfaceToForm } from 'src/app/shared/types/interface-to-form.type';
import cronValidate from 'cron-validate';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { TooltipModule } from 'primeng/tooltip';
import { FluidModule } from 'primeng/fluid';
import { NgTemplateOutlet } from '@angular/common';
import { AutoCompleteModule } from 'primeng/autocomplete';
import { ToggleButtonModule } from 'primeng/togglebutton';
import { ToastService } from 'src/app/core/services/toast.service';

@Component({
  selector: 'app-settings-page-form',
  imports: [
    ReactiveFormsModule,
    ButtonModule,
    InputTextModule,
    InputNumberModule,
    TranslatePipe,
    TooltipModule,
    FluidModule,
    NgTemplateOutlet,
    AutoCompleteModule,
    ToggleButtonModule,
  ],
  templateUrl: './settings-page-form.html',
  styleUrl: './settings-page-form.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SettingsPageForm {
  private readonly settingsApiService = inject(SettingsApiService);
  private readonly authApiService = inject(AuthApiService);
  private readonly translateService = inject(TranslateService);
  private readonly toastService = inject(ToastService);

  public readonly OnSubmit = output<ISettingUpdate[]>();
  public readonly includeKeys = input<ESettingKey[]>();
  public readonly excludeKeys = input<ESettingKey[]>();

  public readonly ESettingKey = ESettingKey;
  public readonly keyTranslates = this.translateService.instant('SETTINGS.BY_KEY');
  public readonly isLoading = signal<boolean>(false);
  public readonly formArray = new FormArray<FormGroup<TInterfaceToForm<ISetting>>>([]);

  private readonly timezones = toSignal(
    this.settingsApiService.getAvailableTimezones().pipe(catchError(() => of([]))),
  );

  // User info signals
  public readonly userInfo = signal<any>(null);
  public readonly isLoadingUserInfo = signal<boolean>(false);
  public readonly timezonesSearch = signal<string>(null);
  public readonly displayedTimezones = computed<string[]>(() => {
    const timezones = this.timezones();
    let search = this.timezonesSearch();
    if (!search) {
      return timezones;
    }
    search = search.toLocaleLowerCase();
    return timezones.filter((t) => t.toLowerCase().includes(search));
  });

  private cronValidator: ValidatorFn = (control: AbstractControl<string>) => {
    const value = control.value;
    if (!!value) {
      const cv = cronValidate(value);
      return cv.isValid() ? null : { cronValidator: true };
    }
    return null;
  };

  private timezoneValidator: ValidatorFn = (control: AbstractControl<string>) => {
    const value = control.value;
    if (!!value) {
      const timezones = this.timezones();
      const valid = !timezones.length || timezones.includes(value);
      return valid ? null : { timezoneValidator: true };
    }
    return null;
  };

  private urlValidator: ValidatorFn = (control: AbstractControl<string>) => {
    const value = control.value;
    if (!!value) {
      try {
        new URL(value);
        return null;
      } catch {
        return { urlValidator: true };
      }
    }
    return null;
  };

  constructor() {
    this.updateSettings();
    this.loadUserInfo();
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
          let filteredList = list;
          
          // Filter based on includeKeys or excludeKeys
          const includeKeys = this.includeKeys();
          const excludeKeys = this.excludeKeys();
          
          if (includeKeys && includeKeys.length > 0) {
            filteredList = list.filter(item => includeKeys.includes(item.key));
          } else if (excludeKeys && excludeKeys.length > 0) {
            filteredList = list.filter(item => !excludeKeys.includes(item.key));
          }
          
          for (const item of filteredList) {
            const form = this.getFormGroup(item);
            this.formArray.push(form);
          }
        },
        error: (error) => {
          this.toastService.error(error);
        },
      });
  }

  private loadUserInfo(): void {
    this.isLoadingUserInfo.set(true);
    this.authApiService
      .getUserInfo()
      .pipe(
        finalize(() => {
          this.isLoadingUserInfo.set(false);
        }),
        catchError((error) => {
          // Silently fail if user is not authenticated (e.g., using password auth)
          return of(null);
        }),
      )
      .subscribe({
        next: (userInfo) => {
          this.userInfo.set(userInfo);
        },
      });
  }

  private getFormGroup(data: ISetting): FormGroup<TInterfaceToForm<ISetting>> {
    const form = new FormGroup<TInterfaceToForm<ISetting>>({
      key: new FormControl<ESettingKey>(data.key),
      value: new FormControl<any>(data.value, this.getValueValidators(data.key)),
      value_type: new FormControl<ESettingValueType>(data.value_type),
      modified_at: new FormControl<string>({ value: data.modified_at, disabled: true }),
    });

    if (data.key === ESettingKey.CRONTAB_EXPR) {
      form.controls.value.addValidators([this.cronValidator]);
    }

    return form;
  }

  private getValueValidators(key: ESettingKey): ValidatorFn[] {
    switch (key) {
      case ESettingKey.CRONTAB_EXPR:
        return [Validators.required, this.cronValidator];
      case ESettingKey.TIMEZONE:
        return [Validators.required, this.timezoneValidator];
      case ESettingKey.OIDC_WELL_KNOWN_URL:
        return [this.urlValidator];
      case ESettingKey.OIDC_CLIENT_ID:
        return [];
      case ESettingKey.OIDC_REDIRECT_URI:
        return [this.urlValidator];
      default:
        return [];
    }
  }

  public onHintClick(link: string): void {
    if (link) {
      window.open(link, '_blank');
    }
  }

  public onTestNotification(): void {
    this.isLoading.set(true);
    const url = this.formArray.value.find((item) => item.key === ESettingKey.NOTIFICATION_URL)
      .value as string;
    this.settingsApiService
      .test_notification(url)
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

  public onTestOidc(): void {
    this.isLoading.set(true);
    const wellKnownUrl = this.formArray.value.find(
      (item) => item.key === ESettingKey.OIDC_WELL_KNOWN_URL,
    ).value as string;
    
    if (!wellKnownUrl) {
      this.toastService.error('OIDC Well-Known URL is required for testing');
      this.isLoading.set(false);
      return;
    }
    
    this.settingsApiService
      .testOidcConnection(wellKnownUrl)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: (response) => {
          this.toastService.success(`OIDC Connection Test Successful. Provider: ${response.endpoints?.issuer || 'Unknown'}`);
        },
        error: (error) => {
          this.toastService.error(error);
        },
      });
  }

  public submit(): void {
    if (this.formArray.invalid) {
      this.formArray.controls.forEach((c) => {
        if (c.invalid) {
          const vc = c.controls.value;
          vc.markAsTouched();
          vc.markAsDirty();
        }
      });
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
