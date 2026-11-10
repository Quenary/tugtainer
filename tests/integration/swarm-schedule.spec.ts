import { expect, type APIRequestContext } from '@playwright/test';
import { test } from '../fixtures/auth-request.fixture';
import type { Job, JobKind } from '../shared/types/jobs.types';
import { getDocker, removeImageTagIfExists } from '../shared/util/docker.util';
import { imageName, publishFrom } from '../shared/util/registry.util';
import { getHostState } from './progress.util';
import { allowLocalRegistry } from './settings.util';
import {
  createService,
  engineImageDigest,
  ensureSwarmHost,
  listServices,
  patchService,
  pinnedImage,
  skipUnlessTestEngine,
  waitServiceConverged,
  waitServiceRunning,
} from './swarm.util';

test.describe.configure({ mode: 'serial' });

async function waitForKind(
  request: APIRequestContext,
  hostId: number,
  sinceCompleted: number,
  kind: JobKind,
  name: string,
): Promise<Job> {
  let matched: Job | undefined;
  await expect
    .poll(
      async () => {
        const state = await getHostState(request, hostId);
        const jobs = [...(state?.completed ?? []).slice(sinceCompleted)];
        if (state?.current) {
          jobs.push(state.current);
        }
        matched = [...jobs]
          .reverse()
          .find(
            (job) =>
              job.kind === kind &&
              Boolean(job.containers?.[name]) &&
              (job.status === 'DONE' || job.status === 'ERROR'),
          );
        return matched?.status ?? 'pending';
      },
      { timeout: 540_000, intervals: [1000, 2000, 5000] },
    )
    .toBe('DONE');
  if (!matched) {
    throw new Error(`missing ${kind} job for ${name}`);
  }
  return matched;
}

test.describe('swarm scheduled check and update', () => {
  test.setTimeout(600_000);

  test('global check and update include an enabled service', async ({
    authorizedRequest: request,
  }, testInfo) => {
    const docker = getDocker();
    await skipUnlessTestEngine(docker);
    await allowLocalRegistry(request);
    const host = await ensureSwarmHost(request);
    const suffix = `sched-${testInfo.workerIndex}-${testInfo.parallelIndex}`;
    const image = imageName(`tugtainer-test/swarm-${suffix}`, 'app');
    await publishFrom(docker, 'alpine:3.20', image);
    const created = await createService({
      suffix,
      image: pinnedImage(image, await engineImageDigest(docker, image)),
    });
    try {
      await waitServiceRunning(docker, created.name);
      await patchService(request, host.id, created.name, {
        check_enabled: true,
        update_enabled: true,
      });
      await publishFrom(docker, 'alpine:3.21', image);
      await removeImageTagIfExists(docker, image);
      const nextDigest = await engineImageDigest(docker, image);

      const before = await getHostState(request, host.id);
      const since = before?.completed?.length ?? 0;
      const checkRes = await request.post('/api/containers/check');
      expect(checkRes.ok(), await checkRes.text()).toBeTruthy();
      const checkJob = await waitForKind(
        request,
        host.id,
        since,
        'check_services',
        created.name,
      );
      expect(checkJob.containers?.[created.name]?.result?.result).toMatch(
        /^available/,
      );
      const listed = await listServices(request, host.id);
      expect(
        listed.find((row) => row.name === created.name)?.update_available,
      ).toBe(true);

      const afterCheck = await getHostState(request, host.id);
      const sinceUpdate = afterCheck?.completed?.length ?? 0;
      const updateRes = await request.post('/api/containers/update');
      expect(updateRes.ok(), await updateRes.text()).toBeTruthy();
      const updateJob = await waitForKind(
        request,
        host.id,
        sinceUpdate,
        'update_services',
        created.name,
      );
      expect(updateJob.containers?.[created.name]?.result?.result).toBe(
        'updated',
      );
      await waitServiceConverged(docker, created.id, created.name, nextDigest, {
        requireCompleted: true,
      });
    } finally {
      await created.cleanup();
      await removeImageTagIfExists(docker, image);
    }
  });
});
