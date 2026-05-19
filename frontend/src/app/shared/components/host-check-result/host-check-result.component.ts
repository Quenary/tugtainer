import { ChangeDetectionStrategy, Component, input } from '@angular/core';
import {
  ContainerCheckResultSeverity,
  IHostActionResult,
} from '@shared/interfaces/check-result.interface';
import { TagModule } from 'primeng/tag';

/**
 * Displaying check result of host
 */
@Component({
  selector: 'app-host-check-result',
  imports: [TagModule],
  templateUrl: './host-check-result.component.html',
  styleUrl: './host-check-result.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HostCheckResultComponent {
  public readonly result = input.required<IHostActionResult>();

  protected readonly ContainerCheckResultSeverity =
    ContainerCheckResultSeverity;
}
