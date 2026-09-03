import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnDestroy,
  signal,
} from '@angular/core';
import { takeUntilDestroyed, toObservable } from '@angular/core/rxjs-interop';
import {
  AbstractControl,
  FormControl,
  FormGroup,
  ReactiveFormsModule,
  ValidatorFn,
  Validators,
} from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { AccordionModule } from 'primeng/accordion';
import { AutoCompleteModule } from 'primeng/autocomplete';
import { ButtonModule } from 'primeng/button';
import { FieldsetModule } from 'primeng/fieldset';
import { FluidModule } from 'primeng/fluid';
import { IftaLabelModule } from 'primeng/iftalabel';
import { InputTextModule } from 'primeng/inputtext';
import { ToggleSwitchModule } from 'primeng/toggleswitch';
import {
  IHostCreate,
  IHostInfo,
  IHostUpdate,
} from 'src/app/features/hosts/hosts.interface';
import { TInterfaceToForm } from '@shared/types/interface-to-form.type';
import { RouterLink } from '@angular/router';
import { ButtonGroup } from 'primeng/buttongroup';
import { ConfirmPopupModule } from 'primeng/confirmpopup';
import { ConfirmationService } from 'primeng/api';
import { PasswordModule } from 'primeng/password';
import { TooltipModule } from 'primeng/tooltip';
import { DeployGuidelineUrl } from 'src/app/app.consts';
import { InputNumberModule } from 'primeng/inputnumber';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { BooleanFieldComponent } from '@shared/components/boolean-field/boolean-field.component';
import { HostsStore } from '../hosts.store';
import { TagModule } from 'primeng/tag';
import { TextareaModule } from 'primeng/textarea';
import { distinctUntilChanged } from 'rxjs';

@Component({
  selector: 'app-host-card',
  imports: [
    AccordionModule,
    ReactiveFormsModule,
    FieldsetModule,
    IftaLabelModule,
    ButtonModule,
    AutoCompleteModule,
    InputTextModule,
    ToggleSwitchModule,
    TranslatePipe,
    FluidModule,
    RouterLink,
    ButtonGroup,
    AutoCompleteModule,
    ConfirmPopupModule,
    PasswordModule,
    TooltipModule,
    InputNumberModule,
    IconFieldModule,
    InputIconModule,
    BooleanFieldComponent,
    TagModule,
    TextareaModule,
  ],
  providers: [ConfirmationService],
  templateUrl: './hosts-card.component.html',
  styleUrl: './hosts-card.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HostsCardComponent implements OnDestroy {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly translateService = inject(TranslateService);
  private readonly confirmationService = inject(ConfirmationService);
  protected readonly hostsStore = inject(HostsStore);

  protected readonly saveTitle = computed(() => {
    const id = this.hostsStore.selectedId();
    return id
      ? this.translateService.instant('GENERAL.SAVE')
      : this.translateService.instant('GENERAL.ADD');
  });
  protected readonly accordionValue = signal<
    string | number | string[] | number[]
  >(['help', 'main']);

  private get defaultFormValues(): Partial<IHostUpdate> {
    return {
      enabled: true,
      prune: false,
      prune_all: false,
      timeout: 5,
      container_hc_timeout: 60,
      ssl: true,
      ssl_ca: null,
      is_changing_secret: false,
      secret: null,
    };
  }

  private readonly urlValidator: ValidatorFn = (control: AbstractControl) => {
    if (!control.value) {
      return null;
    }
    try {
      new URL(control.value);
      return null;
    } catch {
      return { urlValidator: true };
    }
  };

  public readonly form = new FormGroup<TInterfaceToForm<IHostUpdate>>({
    name: new FormControl<string>(null, [Validators.required]),
    enabled: new FormControl<boolean>(null, [Validators.required]),
    prune: new FormControl<boolean>(null, [Validators.required]),
    prune_all: new FormControl<boolean>(null, [Validators.required]),
    url: new FormControl<string>(null, [
      Validators.required,
      this.urlValidator,
      Validators.pattern(/^(http|https):\/\//),
    ]),
    is_changing_secret: new FormControl<boolean>(false),
    secret: new FormControl<string>(null),
    ssl: new FormControl<boolean>(true),
    ssl_ca: new FormControl<string | null>(null),
    timeout: new FormControl<number>(null, [Validators.required]),
    container_hc_timeout: new FormControl(null, [Validators.required]),
  });

  constructor() {
    this.activatedRoute.params
      .pipe(takeUntilDestroyed())
      .subscribe((params) => {
        const id = Number(params['id']) || null;
        this.hostsStore.select(id);
      });

    const keys = Object.keys(this.form.controls);
    toObservable(this.hostsStore.selected)
      .pipe(
        distinctUntilChanged((a, b) => keys.every((k) => a?.[k] === b?.[k])),
        takeUntilDestroyed(),
      )
      .subscribe({
        next: (info) => {
          this.prepareForm(info);
        },
      });

    this.form.controls.prune.valueChanges
      .pipe(takeUntilDestroyed())
      .subscribe((value) => {
        const prune_all = this.form.controls.prune_all;
        if (!value) {
          prune_all.setValue(false);
          prune_all.disable();
        } else {
          prune_all.enable();
        }
      });

    this.form.controls.is_changing_secret.valueChanges
      .pipe(takeUntilDestroyed())
      .subscribe((isChangingSecret) => {
        const control = this.form.controls.secret;
        control.setValue(null);
        if (isChangingSecret) {
          control.enable();
        } else {
          control.disable();
        }
      });
  }

  ngOnDestroy(): void {
    this.hostsStore.select(null);
  }

  private prepareForm(info: IHostInfo | null): void {
    this.form.reset(this.defaultFormValues);
    if (info) {
      this.form.patchValue(info);
    }
    if (this.hostsStore.selectedId()) {
      this.form.controls.secret.disable();
    } else {
      this.form.controls.secret.enable();
    }
  }

  public save(): void {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      this.form.markAllAsDirty();
      return;
    }
    const id = this.hostsStore.selectedId();
    const body = this.form.getRawValue();
    if (id) {
      this.hostsStore.update({ id, body });
    } else {
      const { is_changing_secret: _, ...createBody } = body;
      this.hostsStore.create({ body: createBody as IHostCreate });
    }
  }

  confirmDelete($event: Event): void {
    this.confirmationService.confirm({
      target: $event.currentTarget,
      message: this.translateService.instant('HOSTS.CARD.DELETE_CONFIRM'),
      rejectButtonProps: {
        label: this.translateService.instant('GENERAL.CANCEL'),
        severity: 'secondary',
        outlined: true,
      },
      acceptButtonProps: {
        label: this.translateService.instant('GENERAL.CONFIRM'),
        severity: 'warn',
      },
      accept: () => {
        this.hostsStore.delete({
          id: this.hostsStore.selectedId(),
        });
      },
    });
  }

  public openHelp(): void {
    window.open(DeployGuidelineUrl, '_blank');
  }
}
