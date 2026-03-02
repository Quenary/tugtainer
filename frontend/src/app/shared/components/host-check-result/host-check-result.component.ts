import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { IHostCheckResult } from '@shared/interfaces/check-result.interface';

/**
 * Displaying check result of host
 */
@Component({
  selector: 'app-host-check-result',
  imports: [],
  templateUrl: './host-check-result.component.html',
  styleUrl: './host-check-result.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HostCheckResultComponent {
  public readonly result = input.required<IHostCheckResult>();
}
