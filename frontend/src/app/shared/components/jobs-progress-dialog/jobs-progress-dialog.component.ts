import { NgTemplateOutlet } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import {
  EJobStatus,
  IHostState,
  IJob,
  isHostBusy,
  TJobKind,
} from '@shared/interfaces/jobs.interface';
import { DynamicDialogConfig } from 'primeng/dynamicdialog';
import { TranslatePipe } from '@ngx-translate/core';
import { TagModule } from 'primeng/tag';
import { AccordionModule } from 'primeng/accordion';
import { HostJobsResultComponent } from '../host-jobs-result/host-jobs-result.component';
import { TagSeverity } from '@shared/types/tag-severity.type';

export interface IJobsProgressDialogData {
  current: IJob | null;
  queued: IJob[];
  completed: IJob[];
  pruneResult: string | null;
}

/**
 * Live source for the dialog. `read` is called inside a computed and
 * must touch store signals so the view updates while jobs run.
 */
export interface IJobsProgressDialogSource {
  read: () => {
    jobState?: IHostState | null;
    pruneResult?: string | null;
    extraJobs?: IJob[];
  };
}

export function toJobsProgressDialogData(
  state: IHostState | null | undefined,
  pruneResult: string | null,
  extraJobs: IJob[] = [],
): IJobsProgressDialogData {
  return {
    current: isHostBusy(state) ? (state!.current ?? null) : null,
    queued: state?.queued ?? [],
    completed: [...(state?.completed ?? []), ...extraJobs],
    pruneResult,
  };
}

@Component({
  selector: 'app-jobs-progress-dialog',
  imports: [
    AccordionModule,
    HostJobsResultComponent,
    NgTemplateOutlet,
    TranslatePipe,
    TagModule,
  ],
  templateUrl: './jobs-progress-dialog.component.html',
  styleUrl: './jobs-progress-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class JobsProgressDialogComponent {
  private readonly dynamicDialogConfig: DynamicDialogConfig<IJobsProgressDialogSource> =
    inject(DynamicDialogConfig);

  protected readonly accordionValue = signal<
    string | number | string[] | number[] | null
  >(['current']);

  protected readonly data = computed(() => {
    const snapshot = this.dynamicDialogConfig.data?.read() ?? {};
    return toJobsProgressDialogData(
      snapshot.jobState,
      snapshot.pruneResult ?? null,
      snapshot.extraJobs ?? [],
    );
  });

  protected readonly kindKey: Record<TJobKind, string> = {
    update: 'ACTIONS.JOB_UPDATE',
    check: 'ACTIONS.JOB_CHECK',
  };

  protected readonly kindSeverity: Record<TJobKind, TagSeverity> = {
    update: 'success',
    check: 'info',
  };

  protected readonly statusSeverity: Record<EJobStatus, TagSeverity> = {
    [EJobStatus.ERROR]: 'danger',
    [EJobStatus.DONE]: 'success',
    [EJobStatus.PREPARING]: 'info',
    [EJobStatus.CHECKING]: 'info',
    [EJobStatus.UPDATING]: 'info',
    [EJobStatus.PRUNING]: 'info',
  };
}
