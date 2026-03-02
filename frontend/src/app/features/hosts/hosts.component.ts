import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { HostsTableComponent } from './hosts-table/hosts-table.component';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-hosts',
  imports: [HostsTableComponent, RouterOutlet],
  templateUrl: './hosts.component.html',
  styleUrl: './hosts.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HostsComponent {
  public readonly showTable = signal<boolean>(true);
}
