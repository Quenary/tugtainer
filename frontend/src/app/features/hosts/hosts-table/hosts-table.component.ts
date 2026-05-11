import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  linkedSignal,
  signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { ButtonModule } from 'primeng/button';
import { ButtonGroupModule } from 'primeng/buttongroup';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { InputTextModule } from 'primeng/inputtext';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ToolbarModule } from 'primeng/toolbar';
import { HostStatusComponent } from '@shared/components/host-status/host-status.component';
import { HostsStore, IHostEntity } from '../hosts.store';
import { TooltipModule } from 'primeng/tooltip';
import { DialogModule } from 'primeng/dialog';
import { IHostActionResult } from '@shared/interfaces/check-result.interface';
import { HostCheckResultComponent } from '@shared/components/host-check-result/host-check-result.component';
import { BadgeModule } from 'primeng/badge';

const onlyAvailableStorageKey = 'tugtainer-hosts-only-available';

@Component({
  selector: 'app-hosts-table',
  imports: [
    TableModule,
    ButtonModule,
    TranslatePipe,
    RouterLink,
    IconFieldModule,
    InputIconModule,
    ButtonGroupModule,
    InputTextModule,
    TagModule,
    HostStatusComponent,
    ToolbarModule,
    TooltipModule,
    RouterLink,
    DialogModule,
    HostCheckResultComponent,
    BadgeModule,
  ],
  templateUrl: './hosts-table.component.html',
  styleUrl: './hosts-table.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HostsTableComponent {
  protected readonly hostsStore = inject(HostsStore);

  /**
   * Show only available filter
   */
  protected readonly onlyAvailable = signal<boolean>(
    localStorage.getItemJson(onlyAvailableStorageKey) ?? false,
  );
  /**
   * Hosts displayed in the table. When {@link onlyAvailable} is true,
   * hosts whose containers all have no update available are hidden.
   */
  protected readonly filteredList = computed<IHostEntity[]>(() => {
    const onlyAvailable = this.onlyAvailable();
    const hosts = this.hostsStore.entities();
    return onlyAvailable
      ? hosts.filter((h) => h.available_updates_count > 0)
      : hosts;
  });
  /**
   * Global action dialog visibility
   */
  protected readonly globalActionDialogVisible = linkedSignal<boolean>(() => {
    const globalActionProgress = this.hostsStore.globalActionProgress();
    const globalActionActive = this.hostsStore.globalActionActive();
    return globalActionProgress && !globalActionActive;
  });
  /**
   * List of global action results
   */
  protected readonly globalActionResultList = computed<IHostActionResult[]>(
    () => {
      const globalActionProgress = this.hostsStore.globalActionProgress();
      return globalActionProgress?.result
        ? Object.values(globalActionProgress.result)
        : [];
    },
  );

  constructor() {
    effect(() => {
      const onlyAvailable = this.onlyAvailable();
      localStorage.setItemJson(onlyAvailableStorageKey, onlyAvailable);
    });
  }
}
