import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { IJob } from '@shared/interfaces/jobs.interface';
import {
  ContainerJobOutcomeSeverity,
  TContainerJobOutcome,
} from '@shared/interfaces/jobs-result.interface';
import { TagSeverity } from '@shared/types/tag-severity.type';
import { TagModule } from 'primeng/tag';

export interface IHostJobResultItem {
  id: string;
  name: string;
  result: TContainerJobOutcome;
  severity: TagSeverity | 'contrast';
}

@Component({
  selector: 'app-host-jobs-result',
  imports: [TagModule],
  templateUrl: './host-jobs-result.component.html',
  styleUrl: './host-jobs-result.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HostJobsResultComponent {
  public readonly job = input.required<IJob>();

  protected readonly items = computed<IHostJobResultItem[]>(() => {
    const containers = this.job().containers ?? {};
    return Object.entries(containers)
      .filter(([, slot]) => slot.result != null)
      .map(([slotKey, slot]) => {
        const res = slot.result!;
        let name = slotKey;
        let id = slotKey;

        if ('container' in res && res.container) {
          name = res.container.Name ?? slotKey;
          id = res.container.Id ?? slotKey;
        } else if ('service_name' in res && res.service_name) {
          name = res.service_name;
          id = ('service_id' in res && res.service_id) || res.service_name;
        }

        const outcome = res.result;
        const severity =
          outcome != null
            ? (ContainerJobOutcomeSeverity[outcome] ?? 'contrast')
            : 'contrast';

        return {
          id,
          name,
          result: outcome,
          severity,
        };
      });
  });
}
