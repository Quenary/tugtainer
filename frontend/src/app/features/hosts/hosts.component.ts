import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
} from '@angular/core';
import { HostsTableComponent } from './hosts-table/hosts-table.component';
import { RouterOutlet } from '@angular/router';
import { HostsStore } from './hosts.store';

@Component({
  selector: 'app-hosts',
  imports: [HostsTableComponent, RouterOutlet],
  templateUrl: './hosts.component.html',
  styleUrl: './hosts.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HostsComponent {
  protected readonly hostsStore = inject(HostsStore);
  protected readonly showTable = signal<boolean>(true);

  constructor() {
    this.hostsStore.loadList();
  }
}
