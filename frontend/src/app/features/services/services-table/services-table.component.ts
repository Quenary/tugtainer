import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { rxResource } from '@angular/core/rxjs-interop';
import { FormsModule } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { catchError, map, of } from 'rxjs';
import { ButtonModule } from 'primeng/button';
import { ButtonGroupModule } from 'primeng/buttongroup';
import { DialogModule } from 'primeng/dialog';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { InputTextModule } from 'primeng/inputtext';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ToggleButtonModule } from 'primeng/togglebutton';
import { TooltipModule } from 'primeng/tooltip';
import { ToolbarModule } from 'primeng/toolbar';
import { shouldIncludeHostToJobsDialog } from '@shared/interfaces/jobs.interface';
import { TagSeverity } from '@shared/types/tag-severity.type';
import { ToastService } from 'src/app/core/services/toast.service';
import { HostsStore } from '../../hosts/hosts.store';
import { ServicesStore, IServiceEntity } from '../services.store';
import { ServicesApiService } from '../services-api.service';

export const ServiceUpdateStatusSeverity: Record<string, TagSeverity> = {
  completed: 'success',
  updating: 'info',
  rollback_completed: 'warn',
  rollback_paused: 'danger',
  paused: 'danger',
  failed: 'danger',
};

@Component({
  selector: 'app-services-table',
  imports: [
    TableModule,
    TranslatePipe,
    ToggleButtonModule,
    FormsModule,
    TagModule,
    ButtonModule,
    ButtonGroupModule,
    IconFieldModule,
    InputTextModule,
    InputIconModule,
    TooltipModule,
    DialogModule,
    ToolbarModule,
  ],
  templateUrl: './services-table.component.html',
  styleUrl: './services-table.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ServicesTableComponent {
  protected readonly servicesStore = inject(ServicesStore);
  protected readonly hostsStore = inject(HostsStore);
  private readonly servicesApiService = inject(ServicesApiService);
  private readonly toastService = inject(ToastService);

  protected readonly ServiceUpdateStatusSeverity = ServiceUpdateStatusSeverity;

  protected readonly selected = signal<IServiceEntity[]>([]);
  protected readonly onlyAvailable = signal<boolean>(false);

  protected readonly logsService = signal<IServiceEntity | null>(null);

  protected readonly logsResource = rxResource({
    defaultValue: '',
    params: () => ({
      hostId: this.hostsStore.selectedId(),
      serviceName: this.logsService()?.name,
    }),
    stream: ({ params }) => {
      if (!params.hostId || !params.serviceName) {
        return of('');
      }
      return this.servicesApiService
        .logs(params.hostId, params.serviceName, 200, false)
        .pipe(
          map((logs) => logs || '(No logs)'),
          catchError((err) => {
            this.toastService.error(err);
            return of('(Failed to load logs)');
          }),
        );
    },
  });

  protected readonly hasHostJobsDialog = computed(() => {
    const host = this.hostsStore.selected();
    return shouldIncludeHostToJobsDialog(host?.jobState, host?.pruneResult);
  });

  protected readonly filteredList = computed(() => {
    const onlyAvailable = this.onlyAvailable();
    let list = this.servicesStore.entities();
    if (onlyAvailable) {
      list = list.filter((item) => item.update_available);
    }
    return list;
  });

  protected readonly updatableSelected = computed(() =>
    this.selected().filter((s) => s.update_available),
  );

  constructor() {
    this.servicesStore.loadList();
  }

  protected onCheckSelected(): void {
    const names = this.selected().map((s) => s.name);
    this.servicesStore.checkServices({ names });
    this.selected.set([]);
  }

  protected onUpdateSelected(): void {
    const names = this.updatableSelected().map((s) => s.name);
    this.servicesStore.updateServices({ names });
    this.selected.set([]);
  }

  protected onCheck(service: IServiceEntity): void {
    this.servicesStore.checkServices({ names: [service.name] });
  }

  protected onUpdate(service: IServiceEntity): void {
    this.servicesStore.updateServices({ names: [service.name] });
  }

  protected onCheckEnabledChange(
    check_enabled: boolean,
    service: IServiceEntity,
  ): void {
    this.servicesStore.patchService({
      serviceName: service.name,
      body: { check_enabled },
    });
  }

  protected onUpdateEnabledChange(
    update_enabled: boolean,
    service: IServiceEntity,
  ): void {
    this.servicesStore.patchService({
      serviceName: service.name,
      body: { update_enabled },
    });
  }

  protected openLogs(service: IServiceEntity): void {
    this.logsService.set(service);
  }
}
