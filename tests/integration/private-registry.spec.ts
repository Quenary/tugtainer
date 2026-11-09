import { expect } from '@playwright/test';
import { test } from '../fixtures/auth-request.fixture';
import {
  markUpdateAvailable,
  PRIVATE_REGISTRY_AUTH,
  publishNewerImage,
  startPrivateRegistryContainer,
  UNAUTHORIZED_REGISTRY_AUTH,
} from '../fixtures/private-registry-container.fixture';
import { pickPreservedConfig } from '../shared/util/container-config.util';
import { execInContainer } from '../shared/util/docker.util';
import { jobByNames, jobResults } from '../shared/types/jobs.types';
import { getEnabledHost } from './hosts.util';
import { watchHostJobs } from './progress.util';
import { allowLocalRegistry } from './settings.util';

test.describe.configure({ mode: 'serial' });

test.describe('private registry authentication', () => {
  test.setTimeout(180_000);

  test('checks and updates an image on a registry with a port', async ({
    authorizedRequest: request,
  }, testInfo) => {
    await allowLocalRegistry(request);
    const host = await getEnabledHost(request);
    const created = await startPrivateRegistryContainer({
      suffix: `private-${testInfo.workerIndex}-${testInfo.parallelIndex}`,
      registry: 'localhost:5001',
      auth: PRIVATE_REGISTRY_AUTH,
    });
    try {
      await publishNewerImage(
        created.docker,
        created.image,
        PRIVATE_REGISTRY_AUTH,
      );
      const before = await created.docker.getContainer(created.name).inspect();

      const checkWatch = await watchHostJobs(request, host.id);
      const checkRes = await request.post(
        `/api/containers/check/${host.id}/${created.name}`,
      );
      expect(checkRes.ok(), await checkRes.text()).toBeTruthy();
      const checkState = await checkWatch.waitUntilSettled({
        names: [created.name],
      });
      expect(['available', 'available(notified)']).toContain(
        jobResults(checkState, [created.name])[0]?.result,
      );

      const updateWatch = await watchHostJobs(request, host.id);
      const updateRes = await request.post(
        `/api/containers/update/${host.id}/${created.name}`,
      );
      expect(updateRes.ok(), await updateRes.text()).toBeTruthy();
      const updateState = await updateWatch.waitUntilSettled({
        names: [created.name],
      });
      expect(jobResults(updateState, [created.name])[0]?.result).toBe(
        'updated',
      );

      const after = await created.docker.getContainer(created.name).inspect();
      expect(after.State.Running).toBe(true);
      expect(after.Name).toBe(before.Name);
      expect(after.Id).not.toBe(before.Id);
      expect(after.Image).not.toBe(before.Image);
      expect(pickPreservedConfig(after)).toEqual(pickPreservedConfig(before));
      const marker = await execInContainer(created.docker, created.name, [
        'cat',
        '/data/marker',
      ]);
      expect(marker).toContain('preserved');
    } finally {
      await created.cleanup();
    }
  });

  test('keeps the container when the registry has no credentials', async ({
    authorizedRequest: request,
  }, testInfo) => {
    await allowLocalRegistry(request);
    const host = await getEnabledHost(request);
    const created = await startPrivateRegistryContainer({
      suffix: `unauthorized-${testInfo.workerIndex}-${testInfo.parallelIndex}`,
      registry: 'localhost:5002',
      auth: UNAUTHORIZED_REGISTRY_AUTH,
    });
    try {
      await publishNewerImage(
        created.docker,
        created.image,
        UNAUTHORIZED_REGISTRY_AUTH,
      );
      const before = await created.docker.getContainer(created.name).inspect();

      const checkWatch = await watchHostJobs(request, host.id);
      const checkRes = await request.post(
        `/api/containers/check/${host.id}/${created.name}`,
      );
      expect(checkRes.ok(), await checkRes.text()).toBeTruthy();
      const checkState = await checkWatch.waitUntilSettled({
        names: [created.name],
      });
      expect(
        jobResults(checkState, [created.name])[0]?.result ?? null,
      ).toBeNull();

      // Check cannot read this registry, so it does not mark an update.
      // Force the pull that a recorded update would make.
      await markUpdateAvailable(created.name);
      const updateWatch = await watchHostJobs(request, host.id);
      const updateRes = await request.post(
        `/api/containers/update/${host.id}/${created.name}`,
      );
      expect(updateRes.ok(), await updateRes.text()).toBeTruthy();
      const updateState = await updateWatch.waitUntilSettled({
        names: [created.name],
      });
      const job = jobByNames(updateState, [created.name]);
      expect(job?.containers?.[created.name]?.status).toBe('ERROR');
      expect(
        jobResults(updateState, [created.name])[0]?.result ?? null,
      ).not.toBe('updated');
      expect((job?.log ?? []).join('\n')).toMatch(
        /unauthorized|authentication required|no basic auth credentials/i,
      );

      const after = await created.docker.getContainer(created.name).inspect();
      expect(after.Id).toBe(before.Id);
      expect(after.State.Running).toBe(true);
      expect(after.Name).toBe(before.Name);
      const marker = await execInContainer(created.docker, created.name, [
        'cat',
        '/data/marker',
      ]);
      expect(marker).toContain('preserved');
    } finally {
      await created.cleanup();
    }
  });
});
