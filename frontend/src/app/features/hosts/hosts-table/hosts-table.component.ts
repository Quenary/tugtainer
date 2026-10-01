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
import { Button } from '@openng/optimus-ui/button';
import { ButtonGroup } from '@openng/optimus-ui/buttongroup';
import { IconField } from '@openng/optimus-ui/iconfield';
import { InputIcon } from '@openng/optimus-ui/inputicon';
import { InputText } from '@openng/optimus-ui/inputtext';
import { TableModule } from '@openng/optimus-ui/table';
import { Tag } from '@openng/optimus-ui/tag';
import { Toolbar } from '@openng/optimus-ui/toolbar';
import { HostStatusComponent } from '@shared/components/host-status/host-status.component';
import { HostsStore, IHostEntity } from '../hosts.store';
import { Tooltip } from '@openng/optimus-ui/tooltip';
import { Badge } from '@openng/optimus-ui/badge';

const onlyAvailableStorageKey = 'tugtainer-hosts-only-available';

@Component({
  selector: 'app-hosts-table',
  imports: [
    TableModule,
    Button,
    TranslatePipe,
    RouterLink,
    IconField,
    InputIcon,
    ButtonGroup,
    InputText,
    Tag,
    HostStatusComponent,
    Toolbar,
    Tooltip,
    Badge,
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
