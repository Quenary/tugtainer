import {
  ChangeDetectionStrategy,
  Component,
  computed,
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
import { ICreateHost, IHostInfo, THostClientType } from 'src/app/entities/hosts/hosts-interface';
import { TInterfaceToForm } from 'src/app/shared/types/interface-to-form.type';
import { RouterLink } from '@angular/router';
import { ButtonGroup } from 'primeng/buttongroup';

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
  ],
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

  private get defaultFormValues(): Partial<ICreateHost> {
    return {
      enabled: true,
      prune: false,
    };
  }

  public readonly form = new FormGroup<TInterfaceToForm<ICreateHost>>({
    name: new FormControl<string>(null, [Validators.required]),
    enabled: new FormControl<boolean>(null, [Validators.required]),
    prune: new FormControl<boolean>(null, [Validators.required]),
    config: new FormControl<string>(null),
    context: new FormControl<string>(null),
    host: new FormControl<string>(null),
    tls: new FormControl<boolean>(null),
    tlscacert: new FormControl<string>(null),
    tlscert: new FormControl<string>(null),
    tlskey: new FormControl<string>(null),
    tlsverify: new FormControl<boolean>(null),
    client_binary: new FormControl<string>(null),
    client_call: new FormControl<string[]>(null),
    client_type: new FormControl<THostClientType>(null),
  });

  constructor() {
    this.form.controls.client_call.valueChanges.pipe(takeUntilDestroyed()).subscribe((value) => {
      if (Array.isArray(value) && value.length == 0) {
        this.form.patchValue({
          client_call: null,
        });
      }
    });
  }

  ngOnInit(): void {
    const id = this.id();
    this.getInfo(id);
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
}
