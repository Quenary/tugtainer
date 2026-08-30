import { IContainerJobResult } from './jobs-result.interface';

export enum EJobStatus {
  PREPARING = 'PREPARING',
  CHECKING = 'CHECKING',
  UPDATING = 'UPDATING',
  PRUNING = 'PRUNING',
  DONE = 'DONE',
  ERROR = 'ERROR',
}

export type TJobKind = 'check' | 'update';

export interface IJobBase {
  kind?: TJobKind | null;
  names?: string[] | null;
  status?: EJobStatus;
}

export interface IContainerJob {
  status: EJobStatus;
  result?: IContainerJobResult;
}

export interface IJob extends IJobBase {
  host_id?: number;
  host_name?: string;
  containers?: Record<string, IContainerJob>;
  prune_result?: string | null;
  log?: string[];
}

export interface IHostState {
  status: EJobStatus;
  current?: IJob | null;
  queued?: IJob[];
  completed?: IJob[];
}

export interface IAllHostsState {
  status: EJobStatus;
  hosts?: Record<string, IJob>;
}

export function isHostBusy(
  state: IHostState | IAllHostsState | null | undefined,
): boolean {
  return Boolean(
    state?.status &&
    ![EJobStatus.DONE, EJobStatus.ERROR].includes(state.status),
  );
}

export function isContainerBusy(
  state: IHostState | null | undefined,
  name: string,
): boolean {
  if (!isHostBusy(state)) {
    return false;
  }
  const currentNames = state!.current?.names;
  if (!currentNames) {
    return true;
  }
  if (currentNames.includes(name)) {
    return true;
  }
  return (
    state!.queued?.some((job) => !job.names || job.names.includes(name)) ??
    false
  );
}

export function containerJobSlot(
  state: IHostState | null | undefined,
  name: string,
): IContainerJob | undefined {
  const current = state?.current?.containers?.[name];
  if (current) {
    return current;
  }
  const completed = state?.completed ?? [];
  for (let i = completed.length - 1; i >= 0; i--) {
    const slot = completed[i].containers?.[name];
    if (slot) {
      return slot;
    }
  }
  return undefined;
}

export function hasHostJobsDialog(
  state: IHostState | null | undefined,
  pruneResult?: string | null,
): boolean {
  return Boolean(
    pruneResult ||
    state?.completed?.length ||
    state?.queued?.length ||
    isHostBusy(state),
  );
}
