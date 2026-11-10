import { expect, type APIRequestContext } from '@playwright/test';
import type { HostState, Job } from '../shared/types/jobs.types';

export interface HostJobMatch {
  names?: string[];
  sinceCompleted?: number;
}

function settledMatchingJob(
  state: HostState | null,
  match?: HostJobMatch,
): Job | undefined {
  if (!state) {
    return undefined;
  }
  const since = match?.sinceCompleted ?? 0;
  const candidates = (state.completed ?? []).slice(since);
  if (state.current) {
    candidates.push(state.current);
  }
  const names = match?.names;
  const matches = names?.length
    ? candidates.filter((job) =>
        names.every(
          (name) =>
            (job.names ?? []).includes(name) || Boolean(job.containers?.[name]),
        ),
      )
    : candidates;
  const settled = matches.filter(
    (job) => job.status === 'DONE' || job.status === 'ERROR',
  );
  return settled[settled.length - 1];
}

export async function getHostState(
  request: APIRequestContext,
  hostId: number,
): Promise<HostState | null> {
  const response = await request.get(`/api/containers/progress/${hostId}`);
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as HostState | null;
}

export async function waitUntilHostSettled(
  request: APIRequestContext,
  hostId: number,
  match?: HostJobMatch,
): Promise<HostState> {
  await expect
    .poll(
      async () => {
        const state = await getHostState(request, hostId);
        return settledMatchingJob(state, match)?.status ?? null;
      },
      {
        timeout: 240_000,
        intervals: [500, 1000, 2000],
      },
    )
    .toMatch(/^(DONE|ERROR)$/);

  const state = await getHostState(request, hostId);
  expect(state, 'expected host state to exist').not.toBeNull();
  const job = settledMatchingJob(state, match);
  expect(job?.status).toBe('DONE');
  return state!;
}

/** Snapshot completed-job count before POST so a leftover DONE is not treated as this run. */
export async function watchHostJobs(
  request: APIRequestContext,
  hostId: number,
): Promise<{
  waitUntilSettled: (match?: { names?: string[] }) => Promise<HostState>;
}> {
  const before = await getHostState(request, hostId);
  const sinceCompleted = before?.completed?.length ?? 0;
  return {
    waitUntilSettled: (match) =>
      waitUntilHostSettled(request, hostId, {
        names: match?.names,
        sinceCompleted,
      }),
  };
}
