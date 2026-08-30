export type JobStatus =
  | 'PREPARING'
  | 'CHECKING'
  | 'UPDATING'
  | 'PRUNING'
  | 'DONE'
  | 'ERROR';

export type JobKind = 'check' | 'update';

export type ContainerJobOutcome =
  | 'not_available'
  | 'available'
  | 'available(notified)'
  | 'updated'
  | 'rolled_back'
  | 'failed'
  | null;

export interface ContainerJobResult {
  result?: ContainerJobOutcome;
  image_spec?: string | null;
}

export interface ContainerJob {
  status: JobStatus;
  result?: ContainerJobResult;
}

export interface Job {
  kind?: JobKind | null;
  names?: string[] | null;
  status?: JobStatus;
  host_id?: number;
  host_name?: string;
  containers?: Record<string, ContainerJob>;
  prune_result?: string | null;
}

export interface HostState {
  status: JobStatus;
  current?: Job | null;
  queued?: Job[];
  completed?: Job[];
}

export interface AllHostsState {
  status: JobStatus;
  hosts?: Record<string, Job>;
}

export function latestJob(state: HostState | null | undefined): Job | undefined {
  if (state?.current) {
    return state.current;
  }
  const completed = state?.completed ?? [];
  return completed[completed.length - 1];
}

export function jobByNames(
  state: HostState | null | undefined,
  names: string[],
): Job | undefined {
  const jobs = [
    ...(state?.current ? [state.current] : []),
    ...[...(state?.completed ?? [])].reverse(),
  ];
  return jobs.find((job) =>
    names.every(
      (name) =>
        (job.names ?? []).includes(name) || Boolean(job.containers?.[name]),
    ),
  );
}

export function jobResults(
  state: HostState | null | undefined,
  names?: string[],
): ContainerJobResult[] {
  const job = names?.length ? jobByNames(state, names) : latestJob(state);
  return Object.values(job?.containers ?? {})
    .map((slot) => slot.result)
    .filter((result): result is ContainerJobResult => result != null);
}
