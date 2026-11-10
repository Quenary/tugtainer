import { expect } from '@playwright/test';
import { test } from '../fixtures/auth-request.fixture';
import { jobResults } from '../shared/types/jobs.types';
import { getDocker, removeImageTagIfExists } from '../shared/util/docker.util';
import {
  imageName,
  publishFrom,
  replacePublishedTag,
} from '../shared/util/registry.util';
import { watchHostJobs } from './progress.util';
import { allowLocalRegistry } from './settings.util';
import {
  checkServices,
  createService,
  engineImageDigest,
  ensureSwarmHost,
  listServices,
  pinnedImage,
  serviceImage,
  updateServices,
  waitServiceConverged,
  waitServiceRunning,
} from './swarm.util';

// One host runs a single job at a time.
test.describe.configure({ mode: 'serial' });

test.describe('swarm services', () => {
  test.setTimeout(240_000);

  test('lists a replicated service after the host is refreshed', async ({
    authorizedRequest: request,
  }, testInfo) => {
    const host = await ensureSwarmHost(request);
    const created = await createService({
      suffix: `list-${testInfo.workerIndex}-${testInfo.parallelIndex}`,
      image: 'alpine:3.20',
    });
    try {
      await waitServiceRunning(created.docker, created.name);
      await expect
        .poll(async () => {
          const items = await listServices(request, host.id);
          const item = items.find((service) => service.name === created.name);
          if (!item) {
            return null;
          }
          return {
            mode: item.mode,
            image: item.image.includes('alpine'),
            replicas: `${item.replicas_running}/${item.replicas_desired}`,
          };
        })
        .toEqual({ mode: 'replicated', image: true, replicas: '1/1' });
      expect(host.is_swarm).toBe(true);
    } finally {
      await created.cleanup();
    }
  });

  test('marks a pinned service available when the tag moves', async ({
    authorizedRequest: request,
  }, testInfo) => {
    await allowLocalRegistry(request);
    const host = await ensureSwarmHost(request);
    const suffix = `pin-${testInfo.workerIndex}-${testInfo.parallelIndex}`;
    const image = imageName(`tugtainer-test/swarm-${suffix}`, 'app');
    const docker = getDocker();
    await publishFrom(docker, 'alpine:3.20', image);
    const created = await createService({
      suffix,
      image: pinnedImage(image, await engineImageDigest(docker, image)),
    });
    try {
      await waitServiceRunning(created.docker, created.name);
      await replacePublishedTag(created.docker, 'alpine:3.21', image);
      const watch = await watchHostJobs(request, host.id);
      await checkServices(request, host.id, [created.name]);
      const state = await watch.waitUntilSettled({ names: [created.name] });
      const item = jobResults(state, [created.name])[0];
      expect(['available', 'available(notified)']).toContain(item?.result);

      const listed = await listServices(request, host.id);
      const service = listed.find((row) => row.name === created.name);
      expect(service?.update_available).toBe(true);
    } finally {
      await created.cleanup();
      await removeImageTagIfExists(created.docker, image);
    }
  });

  test('updates a pinned service onto the new digest', async ({
    authorizedRequest: request,
  }, testInfo) => {
    await allowLocalRegistry(request);
    const host = await ensureSwarmHost(request);
    const suffix = `upd-${testInfo.workerIndex}-${testInfo.parallelIndex}`;
    const image = imageName(`tugtainer-test/swarm-${suffix}`, 'app');
    const docker = getDocker();
    await publishFrom(docker, 'alpine:3.20', image);
    const created = await createService({
      suffix,
      image: pinnedImage(image, await engineImageDigest(docker, image)),
    });
    try {
      await waitServiceRunning(created.docker, created.name);
      await publishFrom(docker, 'alpine:3.21', image);
      await removeImageTagIfExists(docker, image);
      const nextDigest = await engineImageDigest(docker, image);
      const watch = await watchHostJobs(request, host.id);
      await checkServices(request, host.id, [created.name]);
      await watch.waitUntilSettled({ names: [created.name] });

      const updateWatch = await watchHostJobs(request, host.id);
      await updateServices(request, host.id, [created.name]);
      const state = await updateWatch.waitUntilSettled({
        names: [created.name],
      });
      expect(jobResults(state, [created.name])[0]?.result).toBe('updated');

      await waitServiceConverged(
        created.docker,
        created.id,
        created.name,
        nextDigest,
        { requireCompleted: true },
      );
      expect(await serviceImage(created.docker, created.id)).toContain(
        `@${nextDigest}`,
      );
      const listed = await listServices(request, host.id);
      expect(
        listed.find((row) => row.name === created.name)?.update_available,
      ).toBe(false);
    } finally {
      await created.cleanup();
      await removeImageTagIfExists(docker, image);
    }
  });

  test('pins a tag-only service to the registry digest', async ({
    authorizedRequest: request,
  }, testInfo) => {
    await allowLocalRegistry(request);
    const host = await ensureSwarmHost(request);
    const suffix = `tag-${testInfo.workerIndex}-${testInfo.parallelIndex}`;
    const image = imageName(`tugtainer-test/swarm-${suffix}`, 'app');
    const docker = getDocker();
    await publishFrom(docker, 'alpine:3.20', image);
    const digest = await engineImageDigest(docker, image);
    const created = await createService({ suffix, image });
    try {
      await waitServiceRunning(created.docker, created.name);
      const watch = await watchHostJobs(request, host.id);
      await updateServices(request, host.id, [created.name]);
      const state = await watch.waitUntilSettled({ names: [created.name] });
      // Swarm may pin the tag while creating the service. Either way the
      // stored image has to carry this registry digest.
      expect(['updated', 'not_available']).toContain(
        jobResults(state, [created.name])[0]?.result,
      );
      await waitServiceConverged(
        created.docker,
        created.id,
        created.name,
        digest,
      );
      expect(await serviceImage(created.docker, created.id)).toContain(
        `@${digest}`,
      );
    } finally {
      await created.cleanup();
      await removeImageTagIfExists(docker, image);
    }
  });

  test('reports an error when the tag was never pushed', async ({
    authorizedRequest: request,
  }, testInfo) => {
    await allowLocalRegistry(request);
    const host = await ensureSwarmHost(request);
    const suffix = `miss-${testInfo.workerIndex}-${testInfo.parallelIndex}`;
    const image = imageName(`tugtainer-test/swarm-${suffix}`, 'absent');
    const created = await createService({ suffix, image });
    try {
      const watch = await watchHostJobs(request, host.id);
      await updateServices(request, host.id, [created.name]);
      const state = await watch.waitUntilSettled({ names: [created.name] });
      const item = jobResults(state, [created.name])[0];
      expect(item?.result).toBe('failed');
      expect(item?.error).toBeTruthy();
    } finally {
      await created.cleanup();
    }
  });

  test('container update leaves the swarm task running', async ({
    authorizedRequest: request,
  }, testInfo) => {
    const host = await ensureSwarmHost(request);
    const created = await createService({
      suffix: `task-${testInfo.workerIndex}-${testInfo.parallelIndex}`,
      image: 'alpine:3.20',
    });
    try {
      await waitServiceRunning(created.docker, created.name);
      const listed = await created.docker.listContainers({
        all: true,
        filters: {
          label: [`com.docker.swarm.service.name=${created.name}`],
        },
      });
      const taskName = listed[0]?.Names?.[0]?.replace(/^\//, '');
      expect(taskName, 'expected a swarm task container').toBeTruthy();

      const watch = await watchHostJobs(request, host.id);
      const updateRes = await request.post(
        `/api/containers/update/${host.id}/${encodeURIComponent(taskName!)}`,
      );
      expect(updateRes.ok(), await updateRes.text()).toBeTruthy();
      const state = await watch.waitUntilSettled({ names: [taskName!] });
      const outcome = jobResults(state, [taskName!])[0]?.result;
      expect(outcome).not.toBe('updated');

      const inspect = await created.docker.getContainer(taskName!).inspect();
      expect(inspect.State.Running).toBe(true);
    } finally {
      await created.cleanup();
    }
  });

  test('does not report an already current service as updated', async ({
    authorizedRequest: request,
  }, testInfo) => {
    await allowLocalRegistry(request);
    const host = await ensureSwarmHost(request);
    const suffix = `noop-${testInfo.workerIndex}-${testInfo.parallelIndex}`;
    const image = imageName(`tugtainer-test/swarm-${suffix}`, 'app');
    const docker = getDocker();
    await publishFrom(docker, 'alpine:3.20', image);
    const created = await createService({
      suffix,
      image: pinnedImage(image, await engineImageDigest(docker, image)),
    });
    try {
      await waitServiceRunning(created.docker, created.name);
      const watch = await watchHostJobs(request, host.id);
      await updateServices(request, host.id, [created.name]);
      const state = await watch.waitUntilSettled({ names: [created.name] });
      expect(jobResults(state, [created.name])[0]?.result).toBe(
        'not_available',
      );
    } finally {
      await created.cleanup();
      await removeImageTagIfExists(docker, image);
    }
  });
});
