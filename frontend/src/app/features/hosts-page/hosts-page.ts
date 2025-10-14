import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { HostsPageTable } from './hosts-page-table/hosts-page-table';
import { NavigationEnd, Router, RouterOutlet } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { filter, map } from 'rxjs';

@Component({
  selector: 'app-host-page',
  imports: [HostsPageTable, RouterOutlet],
  templateUrl: './hosts-page.html',
  styleUrl: './hosts-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HostsPage {
  private readonly router = inject(Router);
  public readonly showTable = signal<boolean>(true);
  // public readonly showTable = toSignal(
  //   this.router.events.pipe(
  //     filter((e) => e instanceof NavigationEnd),
  //     map(() => !this.router.url.includes('/host/')),
  //   ),
  // );
}
