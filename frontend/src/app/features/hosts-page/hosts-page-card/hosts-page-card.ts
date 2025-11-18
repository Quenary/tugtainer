import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { FormControl, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { AccordionModule } from 'primeng/accordion';
import { AutoCompleteModule } from 'primeng/autocomplete';
import { ButtonModule } from 'primeng/button';
import { FieldsetModule } from 'primeng/fieldset';
import { FluidModule } from 'primeng/fluid';
import { IftaLabelModule } from 'primeng/iftalabel';
import { InputTextModule } from 'primeng/inputtext';
import { ToggleSwitchModule } from 'primeng/toggleswitch';
import { finalize, map } from 'rxjs';
import { ToastService } from 'src/app/core/services/toast.service';
import { HostsApiService } from 'src/app/entities/hosts/hosts-api.service';
import { ICreateHost, IHostInfo } from 'src/app/entities/hosts/hosts-interface';
import { TInterfaceToForm } from 'src/app/shared/types/interface-to-form.type';
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

@Component({
  selector: 'app-host-page-card',
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
  ],
  providers: [ConfirmationService],
  templateUrl: './hosts-page-card.html',
  styleUrl: './hosts-page-card.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HostsPageCard implements OnInit {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly toastService = inject(ToastService);
  private readonly hostsApiService = inject(HostsApiService);
  private readonly translateService = inject(TranslateService);
  private readonly router = inject(Router);
  private readonly confirmationService = inject(ConfirmationService);
  private readonly destroyRef = inject(DestroyRef);

  public readonly id = toSignal(
    this.activatedRoute.params.pipe(map((params) => Number(params.id) || null)),
  );
  public readonly saveTitle = computed(() => {
    const id = this.id();
    return id
      ? this.translateService.instant('GENERAL.SAVE')
      : this.translateService.instant('GENERAL.ADD');
  });
  public readonly isLoading = signal<boolean>(false);
  public readonly accordionValue = signal<string | number | string[] | number[]>(['help', 'main']);

  private get defaultFormValues(): Partial<ICreateHost> {
    return {
      enabled: true,
      prune: false,
      prune_all: false,
      timeout: 5,
    };
  }

  public readonly form = new FormGroup<TInterfaceToForm<ICreateHost>>({
    name: new FormControl<string>(null, [Validators.required]),
    enabled: new FormControl<boolean>(null, [Validators.required]),
    prune: new FormControl<boolean>(null, [Validators.required]),
    prune_all: new FormControl<boolean>(null, [Validators.required]),
    url: new FormControl<string>(null, [Validators.required]),
    secret: new FormControl<string>(null),
    timeout: new FormControl<number>(null, [Validators.required]),
  });

  ngOnInit(): void {
    const id = this.id();
    this.getInfo(id);
    this.form.controls.prune.valueChanges
      .pipe(takeUntilDestroyed(this.destroyRef))
      .subscribe((value) => {
        const prune_all = this.form.controls.prune_all;
        if (!value) {
          prune_all.setValue(false);
          prune_all.disable();
        } else {
          prune_all.enable();
        }
      });
  }

  private getInfo(id: number): void {
    if (!id) {
      this.prepareForm(null);
      return;
    }
    this.isLoading.set(true);
    this.hostsApiService
      .read(id)
      .pipe(
        finalize(() => {
          this.isLoading.set(false);
        }),
      )
      .subscribe({
        next: (info) => {
          this.prepareForm(info);
        },
        error: (error) => {
          this.toastService.error(error);
        },
      });
  }

  private prepareForm(info: IHostInfo): void {
    this.form.reset(this.defaultFormValues);
    if (info) {
      this.form.patchValue(info);
    }
  }

  public save(): void {
    if (this.form.invalid) {
      const controls = this.form.controls;
      for (const k in controls) {
        if (controls[k].invalid) {
          controls[k].markAsTouched();
          controls[k].markAsDirty();
        }
      }
      return;
    }
    const id = this.id();
    const body = this.form.getRawValue();
    const req$ = id ? this.hostsApiService.update(id, body) : this.hostsApiService.create(body);
    this.isLoading.set(true);
    req$
      .pipe(
        finalize(() => {
          this.isLoading.set(false);
        }),
      )
      .subscribe({
        next: (info) => {
          if (!id) {
            this.router.navigate([`/hosts/${info.id}`], { replaceUrl: true });
          }
          this.prepareForm(info);
        },
        error: (error) => {
          this.toastService.error(error);
        },
      });
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
        this.deleteHost();
      },
    });
  }

  private deleteHost(): void {
    const id = this.id();
    this.isLoading.set(true);
    this.hostsApiService
      .delete(id)
      .pipe(finalize(() => this.isLoading.set(false)))
      .subscribe({
        next: () => {
          this.toastService.success(this.translateService.instant('SUCCESS'));
          this.router.navigate(['/hosts'], { replaceUrl: true });
        },
        error: (error) => {
          this.toastService.error(error);
        },
      });
  }

  public openHelp(): void {
    window.open(DeployGuidelineUrl, '_blank');
  }
}
