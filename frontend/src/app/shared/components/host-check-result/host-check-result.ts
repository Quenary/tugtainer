import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import { IHostCheckResult } from 'src/app/entities/check/check-result.interface';

/**
 * Displaying check result of host
 */
@Component({
  selector: 'app-host-check-result',
  imports: [],
  templateUrl: './host-check-result.html',
  styleUrl: './host-check-result.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HostCheckResult {
  public readonly result = input.required<IHostCheckResult>();
}
