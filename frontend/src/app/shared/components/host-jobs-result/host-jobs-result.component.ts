import {
  ChangeDetectionStrategy,
  Component,
  computed,
  input,
} from '@angular/core';
import { IContainerJob, IJob } from '@shared/interfaces/jobs.interface';
import {
  ContainerJobOutcomeSeverity,
  IContainerJobResult,
} from '@shared/interfaces/jobs-result.interface';
import { TagModule } from 'primeng/tag';

type ContainerJobSlotWithResult = IContainerJob & {
  result: IContainerJobResult;
};

@Component({
  selector: 'app-host-jobs-result',
  imports: [TagModule],
  templateUrl: './host-jobs-result.component.html',
  styleUrl: './host-jobs-result.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class HostJobsResultComponent {
  public readonly job = input.required<IJob>();

  protected readonly ContainerJobOutcomeSeverity = ContainerJobOutcomeSeverity;

  protected readonly containerSlots = computed(() =>
    Object.values(this.job().containers ?? {}).filter(
      (slot): slot is ContainerJobSlotWithResult => slot.result != null,
    ),
  );
}
