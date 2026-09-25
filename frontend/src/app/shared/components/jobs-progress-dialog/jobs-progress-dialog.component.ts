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
import { ProgressSpinnerModule } from 'primeng/progressspinner';

export interface IJobsProgressHostData {
  hostId: number;
  hostName: string;
  current: IJob | null;
  queued: IJob[];
  completed: IJob[];
  pruneResult: string | null;
}

export interface IJobsProgressDialogData {
  hosts: IJobsProgressHostData[];
}

/**
 * Live source for the dialog. `read` is called inside a computed and
 * must touch store signals so the view updates while jobs run.
 */
export interface IJobsProgressDialogSource {
  read: () => {
    hosts: {
      hostId: number;
      hostName: string;
      jobState: IHostState | null;
      pruneResult: string | null;
    }[];
  };
}

export function toJobsProgressDialogData(
  state: IHostState | null | undefined,
  pruneResult: string | null,
  hostId = 0,
  hostName = '',
): IJobsProgressHostData {
  return {
    hostId,
    hostName,
    current: isHostBusy(state) ? (state!.current ?? null) : null,
    queued: state?.queued ?? [],
    completed: state?.completed ?? [],
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
    ProgressSpinnerModule,
  ],
  templateUrl: './jobs-progress-dialog.component.html',
  styleUrl: './jobs-progress-dialog.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class JobsProgressDialogComponent {
  private readonly dynamicDialogConfig: DynamicDialogConfig<IJobsProgressDialogSource> =
    inject(DynamicDialogConfig);

  private readonly _accordionValues = signal<Record<number, string[]>>({});

  protected getAccordionValue(hostId: number): string[] {
    const vals = this._accordionValues();
    return vals[hostId] ?? ['current'];
  }

  protected setAccordionValue(
    hostId: number,
    value: string | string[] | number | number[] | null | undefined,
  ): void {
    const arr = Array.isArray(value) ? value : value != null ? [value] : [];
    this._accordionValues.update((v) => ({ ...v, [hostId]: arr as string[] }));
  }

  protected readonly data = computed<IJobsProgressDialogData>(() => {
    const snapshot = this.dynamicDialogConfig.data?.read() ?? { hosts: [] };
    return {
      hosts: snapshot.hosts.map((h) =>
        toJobsProgressDialogData(
          h.jobState,
          h.pruneResult,
          h.hostId,
          h.hostName,
        ),
      ),
    };
  });

  protected readonly kindKey: Record<TJobKind, string> = {
    update: 'ACTIONS.JOB_UPDATE',
    check: 'ACTIONS.JOB_CHECK',
    update_services: 'ACTIONS.JOB_UPDATE_SERVICES',
    check_services: 'ACTIONS.JOB_CHECK_SERVICES',
  };

  protected readonly kindSeverity: Record<TJobKind, TagSeverity> = {
    update: 'success',
    check: 'info',
    update_services: 'success',
    check_services: 'info',
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
