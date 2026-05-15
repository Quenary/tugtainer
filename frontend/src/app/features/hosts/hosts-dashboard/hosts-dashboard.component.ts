import {
  ChangeDetectionStrategy,
  Component,
  inject,
  model,
  OnDestroy,
  signal,
} from '@angular/core';
import { HostsStore } from '../hosts.store';
import { ActivatedRoute, RouterLink, RouterOutlet } from '@angular/router';
import { CardModule } from 'primeng/card';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { TagModule } from 'primeng/tag';
import { HostStatusComponent } from '@shared/components/host-status/host-status.component';
import { ButtonModule } from 'primeng/button';
import { ButtonGroupModule } from 'primeng/buttongroup';
import { ConfirmPopupModule } from 'primeng/confirmpopup';
import { BooleanFieldComponent } from '@shared/components/boolean-field/boolean-field.component';
import { FormsModule } from '@angular/forms';
import { TooltipModule } from 'primeng/tooltip';
import { ConfirmationService } from 'primeng/api';
import { ToggleSwitchModule } from 'primeng/toggleswitch';

@Component({
  selector: 'app-hosts-dashboard',
  imports: [
    RouterOutlet,
    CardModule,
    TranslatePipe,
    RouterLink,
    TagModule,
    HostStatusComponent,
    ButtonModule,
    ButtonGroupModule,
    ConfirmPopupModule,
    BooleanFieldComponent,
    FormsModule,
    TooltipModule,
    ToggleSwitchModule,
  ],
  providers: [ConfirmationService],
  templateUrl: './hosts-dashboard.component.html',
  styleUrl: './hosts-dashboard.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HostsDashboardComponent implements OnDestroy {
  protected readonly hostsStore = inject(HostsStore);
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly confirmationService = inject(ConfirmationService);
  private readonly translateService = inject(TranslateService);

  protected readonly childActive = signal<boolean>(false);
  protected readonly pruneAll = model<boolean>(false);

  constructor() {
    this.activatedRoute.params
      .pipe(takeUntilDestroyed())
      .subscribe((params) => {
        const id = Number(params['id']) || null;
        this.hostsStore.select(id);
      });
  }

  ngOnDestroy(): void {
    this.hostsStore.select(null);
  }

  protected confirmPrune($event: Event): void {
    this.confirmationService.confirm({
      target: $event.currentTarget,
      rejectButtonProps: {
        label: this.translateService.instant('GENERAL.CANCEL'),
        severity: 'secondary',
        outlined: true,
      },
      acceptButtonProps: {
        label: this.translateService.instant('GENERAL.CONFIRM'),
        severity: 'danger',
      },
      accept: () => {
        this.hostsStore.pruneHost({
          id: this.hostsStore.selectedId(),
          body: {
            all: this.pruneAll(),
          },
        });
      },
    });
  }
}
