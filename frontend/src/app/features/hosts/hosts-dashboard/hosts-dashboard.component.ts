import {
  ChangeDetectionStrategy,
  Component,
  inject,
  linkedSignal,
  model,
  OnDestroy,
  signal,
  computed,
} from '@angular/core';
import { takeUntilDestroyed, toSignal } from '@angular/core/rxjs-interop';
import { BreakpointObserver, Breakpoints } from '@angular/cdk/layout';
import { map } from 'rxjs';
import { HostsStore } from '../hosts.store';
import { ActivatedRoute, RouterLink, RouterOutlet } from '@angular/router';
import { Card } from '@openng/optimus-ui/card';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { Tag } from '@openng/optimus-ui/tag';
import { HostStatusComponent } from '@shared/components/host-status/host-status.component';
import { Button } from '@openng/optimus-ui/button';
import { ButtonGroup } from '@openng/optimus-ui/buttongroup';
import { ConfirmPopup } from '@openng/optimus-ui/confirmpopup';
import { BooleanFieldComponent } from '@shared/components/boolean-field/boolean-field.component';
import { FormsModule } from '@angular/forms';
import { Tooltip } from '@openng/optimus-ui/tooltip';
import { ConfirmationService } from '@openng/optimus-ui/api';
import { ToggleSwitch } from '@openng/optimus-ui/toggleswitch';
import { shouldIncludeHostToJobsDialog } from '@shared/interfaces/jobs.interface';

@Component({
  selector: 'app-hosts-dashboard',
  imports: [
    RouterOutlet,
    Card,
    TranslatePipe,
    RouterLink,
    Tag,
    HostStatusComponent,
    Button,
    ButtonGroup,
    ConfirmPopup,
    BooleanFieldComponent,
    FormsModule,
    Tooltip,
    ToggleSwitch,
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
  protected readonly hasHostJobsDialog = computed(() => {
    const host = this.hostsStore.selected();
    return shouldIncludeHostToJobsDialog(host?.jobState, host?.pruneResult);
  });

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
