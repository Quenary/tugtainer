import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { IHostActionResult } from '@shared/interfaces/check-result.interface';
import { DynamicDialogConfig } from 'primeng/dynamicdialog';
import { HostCheckResultComponent } from '../host-check-result/host-check-result.component';

export interface IActionResultDialogData {
  results: IHostActionResult[];
  pruneResult: string | null;
}

@Component({
  selector: 'app-action-result-dialog',
  imports: [HostCheckResultComponent],
  templateUrl: './action-result-dialog.component.html',
  styleUrl: './action-result-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ActionResultDialogComponent {
  protected readonly dynamicDialogConfig: DynamicDialogConfig<IActionResultDialogData> =
    inject(DynamicDialogConfig);
}
