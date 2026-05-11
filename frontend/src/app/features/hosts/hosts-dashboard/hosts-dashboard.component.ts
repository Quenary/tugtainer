import {
  ChangeDetectionStrategy,
  Component,
  inject,
  OnDestroy,
  signal,
} from '@angular/core';
import { HostsStore } from '../hosts.store';
import { ActivatedRoute, RouterLink, RouterOutlet } from '@angular/router';
import { CardModule } from 'primeng/card';
import { TranslatePipe } from '@ngx-translate/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { TagModule } from 'primeng/tag';
import { HostStatusComponent } from '@shared/components/host-status/host-status.component';
import { ButtonModule } from 'primeng/button';

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
  ],
  templateUrl: './hosts-dashboard.component.html',
  styleUrl: './hosts-dashboard.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HostsDashboardComponent implements OnDestroy {
  protected readonly hostsStore = inject(HostsStore);
  private readonly activatedRoute = inject(ActivatedRoute);

  protected readonly childActive = signal<boolean>(false);

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
}
