import { ChangeDetectionStrategy, Component, ViewChild } from '@angular/core';
import { ContainersPageHeader } from './containers-page-header/containers-page-header';
import { ContainersPageTable } from './containers-page-table/containers-page-table';

@Component({
  selector: 'app-containers-page',
  imports: [ContainersPageHeader, ContainersPageTable],
  templateUrl: './containers-page.html',
  styleUrl: './containers-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainersPage {
  @ViewChild(ContainersPageTable, { static: true, read: ContainersPageTable })
  private readonly containersPageTableRef: ContainersPageTable;

  public onCheckDone(): void {
    this.containersPageTableRef?.updateList();
  }
}
