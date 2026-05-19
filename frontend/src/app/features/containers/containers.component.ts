import {
  ChangeDetectionStrategy,
  Component,
  inject,
  signal,
} from '@angular/core';
import { ContainersTableComponent } from './containers-table/containers-table.component';
import { RouterOutlet } from '@angular/router';
import { ContainersStore } from './containers.store';

@Component({
  selector: 'app-containers',
  imports: [ContainersTableComponent, RouterOutlet],
  templateUrl: './containers.component.html',
  styleUrl: './containers.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainersComponent {
  protected readonly containersStore = inject(ContainersStore);

  /**
   * Whether to show table
   */
  protected readonly showTable = signal<boolean>(true);
}
