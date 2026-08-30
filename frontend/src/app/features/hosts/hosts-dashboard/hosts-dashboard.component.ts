import {
  ChangeDetectionStrategy,
  Component,
  inject,
  linkedSignal,
  model,
  OnDestroy,
  signal,
} from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { map } from 'rxjs';
import { HostsStore } from '../hosts.store';
import { ActivatedRoute, RouterLink, RouterOutlet } from '@angular/router';
import { CardModule } from 'primeng/card';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
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
import { hasHostJobsDialog } from '@shared/interfaces/jobs.interface';

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
  host: {
    '[class.narrow]': 'narrow()',
  },
})
export class HostsDashboardComponent implements OnDestroy {
  protected readonly hostsStore = inject(HostsStore);
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly confirmationService = inject(ConfirmationService);
  private readonly translateService = inject(TranslateService);
  private readonly breakpointObserver = inject(BreakpointObserver);

  private readonly _narrow = toSignal<boolean>(
    this.breakpointObserver
      .observe([Breakpoints.Handset, Breakpoints.Small])
      .pipe(map((result) => result.matches)),
  );
  protected readonly narrow = linkedSignal(this._narrow);

  protected readonly childActive = signal<boolean>(false);
  protected readonly pruneAll = model<boolean>(false);
  protected readonly hasHostJobsDialog = hasHostJobsDialog;

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
