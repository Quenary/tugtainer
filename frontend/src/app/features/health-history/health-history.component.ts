import { DatePipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  inject,
  resource,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { ButtonModule } from 'primeng/button';
import { SelectModule } from 'primeng/select';
import { TableLazyLoadEvent, TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ToolbarModule } from 'primeng/toolbar';
import { firstValueFrom } from 'rxjs';
import { EContainerHealthSeverity } from '../containers/containers.interface';
import { HostsStore } from '../hosts/hosts.store';
import { HealthHistoryApiService } from './health-history-api.service';
import { IHealthHistoryFilterRequest } from './health-history.interface';

@Component({
  selector: 'app-health-history',
  imports: [
    TableModule,
    TagModule,
    DatePipe,
    TranslatePipe,
    RouterLink,
    ButtonModule,
    ToolbarModule,
    SelectModule,
    FormsModule,
  ],
  templateUrl: './health-history.component.html',
  styleUrl: './health-history.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HealthHistoryComponent {
  private readonly hostsStore = inject(HostsStore);
  private readonly healthHistoryApiService = inject(HealthHistoryApiService);

  protected readonly healthSeverity = EContainerHealthSeverity;
  protected readonly statusOptions = ['healthy', 'unhealthy', 'starting'];

  // Signals for filter and pagination state
  protected readonly status = signal<string | null>(null);
  protected readonly page = signal<number>(1);
  protected readonly limit = signal<number>(25);

  // Resource to load health history
  protected readonly healthResource = resource({
    params: () => ({
      host_id: this.hostsStore.selectedId(),
      page: this.page(),
      limit: this.limit(),
      status: this.status(),
    }),
    loader: async (params) => {
      if (!params.params.host_id) return null;
      const req: IHealthHistoryFilterRequest = {
        host_id: params.params.host_id,
        page: params.params.page,
        limit: params.params.limit,
      };
      if (params.params.status) {
        req.status = [params.params.status];
      }
      return firstValueFrom(this.healthHistoryApiService.getHistory(req));
    },
  });

  onStatusChange(status: string | null): void {
    this.status.set(status);
    this.page.set(1);
  }

  onLazyLoad(event: TableLazyLoadEvent): void {
    const limit = event.rows || 25;
    const page = Math.floor((event.first || 0) / limit) + 1;
    this.limit.set(limit);
    this.page.set(page);
  }
}
