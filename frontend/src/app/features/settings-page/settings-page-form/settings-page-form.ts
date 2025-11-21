import {
  ChangeDetectionStrategy,
  ChangeDetectorRef,
  Component,
  computed,
  effect,
  inject,
  output,
  resource,
  signal,
} from '@angular/core';
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
import { catchError, finalize, firstValueFrom, of } from 'rxjs';
import { SettingsApiService } from 'src/app/entities/settings/settings-api.service';
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
  private readonly translateService = inject(TranslateService);
  private readonly toastService = inject(ToastService);
  private readonly changeDetectorRef = inject(ChangeDetectorRef);

  public readonly OnSubmit = output<ISettingUpdate[]>();

  public readonly ESettingKey = ESettingKey;
  public readonly keyTranslates = this.translateService.instant('SETTINGS.BY_KEY');
  public readonly isLoading = signal<boolean>(false);
  public readonly formArray = new FormArray<FormGroup<TInterfaceToForm<ISetting>>>([]);

  private readonly timezones = resource({
    loader: () =>
      firstValueFrom(
        this.settingsApiService.getAvailableTimezones().pipe(
          catchError((error) => {
            this.toastService.error(error);
            return of([]);
          }),
        ),
      ),
    defaultValue: [],
  });

  private readonly settings = resource({
    loader: () =>
      firstValueFrom(
        this.settingsApiService.list().pipe(
          catchError((error) => {
            this.toastService.error(error);
            return of([]);
          }),
        ),
      ),
    defaultValue: [],
  });

  public readonly timezonesSearch = signal<string>(null);
  public readonly displayedTimezones = computed<string[]>(() => {
    const timezones = this.timezones.value();
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
      const timezones = this.timezones.value();
      const valid = !timezones.length || timezones.includes(value);
      return valid ? null : { timezoneValidator: true };
    }
    return null;
  };

  constructor() {
    effect(() => {
      const list = this.settings.value();
      this.formArray.clear();
      for (const item of list) {
        const form = this.getFormGroup(item);
        this.formArray.push(form);
      }
      this.changeDetectorRef.markForCheck();
    });
  }

  private getFormGroup(data: ISetting): FormGroup<TInterfaceToForm<ISetting>> {
    const form = new FormGroup<TInterfaceToForm<ISetting>>({
      key: new FormControl<ESettingKey>(data.key),
      value: new FormControl<any>(data.value, this.getValueValidators(data.key)),
      value_type: new FormControl<ESettingValueType>(data.value_type),
      modified_at: new FormControl<string>({ value: data.modified_at, disabled: true }),
    });
    return form;
  }

  private getValueValidators(key: ESettingKey): ValidatorFn[] {
    switch (key) {
      case ESettingKey.CRONTAB_EXPR:
        return [Validators.required, this.cronValidator];
      case ESettingKey.TIMEZONE:
        return [Validators.required, this.timezoneValidator];
      default:
        return [];
    }
  }

  public onHintClick(link: string): void {
    if (link) {
      window.open(link, '_blank');
    }
  }

  public onTestNotification(url: string): void {
    this.isLoading.set(true);
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
