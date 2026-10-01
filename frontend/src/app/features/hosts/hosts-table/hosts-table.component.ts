import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { ButtonModule } from '@openng/optimus-ui/button';
import { ButtonGroupModule } from '@openng/optimus-ui/buttongroup';
import { IconFieldModule } from '@openng/optimus-ui/iconfield';
import { InputIconModule } from '@openng/optimus-ui/inputicon';
import { InputTextModule } from '@openng/optimus-ui/inputtext';
import { TableModule } from '@openng/optimus-ui/table';
import { TagModule } from '@openng/optimus-ui/tag';
import { ToolbarModule } from '@openng/optimus-ui/toolbar';
import { HostStatusComponent } from '@shared/components/host-status/host-status.component';
import { HostsStore, IHostEntity } from '../hosts.store';
import { TooltipModule } from '@openng/optimus-ui/tooltip';
import { DialogModule } from '@openng/optimus-ui/dialog';
import { BadgeModule } from '@openng/optimus-ui/badge';

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

  constructor() {
    effect(() => {
      const onlyAvailable = this.onlyAvailable();
      localStorage.setItemJson(onlyAvailableStorageKey, onlyAvailable);
    });
  }
}
