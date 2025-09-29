import { ChangeDetectionStrategy, Component } from '@angular/core';
import { ContainersPageTable } from './containers-page-table/containers-page-table';

@Component({
  selector: 'app-containers-page',
  imports: [ContainersPageTable],
  templateUrl: './containers-page.html',
  styleUrl: './containers-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainersPage {}
