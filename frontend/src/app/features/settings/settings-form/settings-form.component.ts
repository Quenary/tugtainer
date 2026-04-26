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
import { catchError, finalize, firstValueFrom, map, of } from 'rxjs';
import { SettingsApiService } from '../settings-api.service';
import {
  ESettingKey,
  ESettingSortIndex,
  ESettingValueType,
  ISetting,
  ISettingUpdate,
  ITestNotificationRequestBody,
} from '../settings.interface';
import { TInterfaceToForm } from '@shared/types/interface-to-form.type';
import cronValidate from 'cron-validate';
import { ButtonModule } from 'primeng/button';
import { InputTextModule } from 'primeng/inputtext';
import { InputNumberModule } from 'primeng/inputnumber';
import { TooltipModule } from 'primeng/tooltip';
import { FluidModule } from 'primeng/fluid';
import { NgTemplateOutlet } from '@angular/common';
import {
  AutoCompleteCompleteEvent,
  AutoCompleteModule,
} from 'primeng/autocomplete';
import { ToastService } from 'src/app/core/services/toast.service';
import { IftaLabelModule } from 'primeng/iftalabel';
import { TextareaModule } from 'primeng/textarea';
import { ToggleSwitchModule } from 'primeng/toggleswitch';
import { BooleanFieldComponent } from '@shared/components/boolean-field/boolean-field.component';

@Component({
  selector: 'app-settings-form',
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
    ToggleSwitchModule,
    IftaLabelModule,
    TextareaModule,
    BooleanFieldComponent,
  ],
  templateUrl: './settings-form.component.html',
  styleUrl: './settings-form.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class SettingsFormComponent {
  private readonly settingsApiService = inject(SettingsApiService);
  private readonly translateService = inject(TranslateService);
  private readonly toastService = inject(ToastService);
  private readonly changeDetectorRef = inject(ChangeDetectorRef);

  public readonly OnSubmit = output<ISettingUpdate[]>();

  protected readonly ESettingKey = ESettingKey;
  protected readonly keyTranslates =
    this.translateService.instant('SETTINGS.BY_KEY');
  protected readonly isLoading = signal<boolean>(false);
  protected readonly formArray = new FormArray<
    FormGroup<TInterfaceToForm<ISetting>>
  >([]);

  private readonly timezones = resource({
    loader: () =>
      firstValueFrom(
        this.settingsApiService.getAvailableTimezones().pipe(
          map((list) => list.sort((a, b) => a.localeCompare(b))),
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
          map((res) =>
            res.sort(
              (a, b) => ESettingSortIndex[a.key] - ESettingSortIndex[b.key],
            ),
          ),
          catchError((error) => {
            this.toastService.error(error);
            return of([]);
          }),
        ),
      ),
    defaultValue: [],
  });

  /**
   * Timezones autocomplete query.
   *
   * This should be an object to "update" list
   * even if query not changed (on autocomplete arrow click).
   */
  protected readonly timezonesAutocompleteEvent =
    signal<AutoCompleteCompleteEvent | null>(null);
  /**
   * Timezones autocomplete list
   */
  protected readonly displayedTimezones = computed<string[]>(() => {
    const timezones = this.timezones.value();
    const timezonesAutocompleteEvent = this.timezonesAutocompleteEvent();
    let query: string = timezonesAutocompleteEvent?.query ?? '';
    if (!query) {
      return [...timezones];
    }
    query = query.toLocaleLowerCase();
    return timezones.filter((t) => t.toLowerCase().includes(query));
  });

  private cronValidator: ValidatorFn = (control: AbstractControl<string>) => {
    const value = control.value;
    if (value) {
      const cv = cronValidate(value);
      return cv.isValid() ? null : { cronValidator: true };
    }
    return null;
  };

  private timezoneValidator: ValidatorFn = (
    control: AbstractControl<string>,
  ) => {
    const value = control.value;
    if (value) {
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
      value: new FormControl<string | number | boolean>(
        data.value,
        this.getValueValidators(data.key),
      ),
      value_type: new FormControl<ESettingValueType>(data.value_type),
      modified_at: new FormControl<string>({
        value: data.modified_at,
        disabled: true,
      }),
    });
    return form;
  }

  private getValueValidators(key: ESettingKey): ValidatorFn[] {
    switch (key) {
      case ESettingKey.CHECK_CRONTAB_EXPR:
      case ESettingKey.UPDATE_CRONTAB_EXPR:
        return [Validators.required, this.cronValidator];
      case ESettingKey.TIMEZONE:
        return [Validators.required, this.timezoneValidator];
      default:
        return [];
    }
  }

  protected onHintClick(link: string): void {
    if (link) {
      window.open(link, '_blank');
    }
  }

  protected onTestNotification(): void {
    const values = this.getSettingsValues();
    const title_template = values.find(
      (item) => item.key == ESettingKey.NOTIFICATION_TITLE_TEMPLATE,
    ).value as string;
    const body_template = values.find(
      (item) => item.key == ESettingKey.NOTIFICATION_BODY_TEMPLATE,
    ).value as string;
    const urls = values.find(
      (item) => item.key == ESettingKey.NOTIFICATION_URLS,
    ).value as string;
    const body: ITestNotificationRequestBody = {
      title_template,
      body_template,
      urls,
    };
    this.isLoading.set(true);
    this.settingsApiService
      .test_notification(body)
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

  protected getSettingsValues(): ISettingUpdate[] {
    return this.formArray.getRawValue().map((item) => ({
      key: item.key,
      value: item.value,
    }));
  }

  protected submit(): void {
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
    const values = this.getSettingsValues();
    this.OnSubmit.emit(values);
  }
}
