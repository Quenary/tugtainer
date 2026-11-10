import { mergeTests, expect } from '@playwright/test';
import type { ContainerListItem } from '../shared/types/containers.types';
import { jobResults } from '../shared/types/jobs.types';
import { test as authTest } from '../fixtures/auth-request.fixture';
import { test as outdatedAlpineContainerTest } from '../fixtures/outdated-alpine-container.fixture';
import { getDocker } from '../shared/util/docker.util';
import { replacePublishedTag } from '../shared/util/registry.util';
import { getEnabledHost } from './hosts.util';
import { watchHostJobs } from './progress.util';
import { startRegistryContainer } from './registry-container.util';
import { allowLocalRegistry } from './settings.util';

export const test = mergeTests(authTest, outdatedAlpineContainerTest);

const PROTECTED_LABEL = 'dev.quenary.tugtainer.protected';

// One host runs a single job at a time. Parallel checks queue behind each
// other and the settle wait expires before the later jobs start.
test.describe.configure({ mode: 'serial' });

test.describe('check container update availability', () => {
  test.setTimeout(180_000);

  test('marks container with outdated image as available', async ({
    authorizedRequest: request,
    outdatedAlpineContainer,
  }) => {
    const host = await getEnabledHost(request);
    const names = [outdatedAlpineContainer.name];
    const watch = await watchHostJobs(request, host.id);

    const checkRes = await request.post(
      `/api/containers/check/${host.id}/${outdatedAlpineContainer.name}`,
    );
    expect(checkRes.ok()).toBeTruthy();
    const cacheId = (await checkRes.json()) as string;
    expect(cacheId).toBeTruthy();

    const state = await watch.waitUntilSettled({ names });

    const results = jobResults(state, names);
    const itemResult =
      results.find(
        (item) => item.image_spec === outdatedAlpineContainer.image,
      ) ?? results[0];
    expect(['available', 'available(notified)']).toContain(itemResult?.result);
    expect(itemResult?.image_spec).toBe(outdatedAlpineContainer.image);

    const listRes = await request.get(`/api/containers/${host.id}/list`);
    expect(listRes.ok()).toBeTruthy();
    const list = (await listRes.json()) as ContainerListItem[];
    const item = list.find((c) => c.name === outdatedAlpineContainer.name);
    expect(item?.update_available).toBe(true);
  });

  test('checks selected names via host endpoint body', async ({
    authorizedRequest: request,
    outdatedAlpineContainer,
  }) => {
    const host = await getEnabledHost(request);
    const names = [outdatedAlpineContainer.name];
    const watch = await watchHostJobs(request, host.id);

    const checkRes = await request.post(`/api/containers/check/${host.id}`, {
      data: {
        names: [outdatedAlpineContainer.name, 'does-not-exist'],
      },
    });
    expect(checkRes.ok()).toBeTruthy();

    const state = await watch.waitUntilSettled({ names });
    const itemResult = jobResults(state, names).find(
      (item) => item.image_spec === outdatedAlpineContainer.image,
    );
    expect(['available', 'available(notified)']).toContain(itemResult?.result);
  });

  test('marks a current registry tag as not available', async ({
    authorizedRequest: request,
  }, testInfo) => {
    await allowLocalRegistry(request);
    const host = await getEnabledHost(request);
    const created = await startRegistryContainer({
      suffix: `current-${testInfo.workerIndex}-${testInfo.parallelIndex}`,
    });
    try {
      const watch = await watchHostJobs(request, host.id);
      const checkRes = await request.post(
        `/api/containers/check/${host.id}/${created.name}`,
      );
      expect(checkRes.ok(), await checkRes.text()).toBeTruthy();
      const state = await watch.waitUntilSettled({ names: [created.name] });
      const item = jobResults(state, [created.name]).find(
        (result) => result.image_spec === created.image,
      );
      expect(item?.result).toBe('not_available');
    } finally {
      await created.cleanup();
    }
  });

  test('marks a newer image on a registry with a port as available', async ({
    authorizedRequest: request,
  }, testInfo) => {
    await allowLocalRegistry(request);
    const host = await getEnabledHost(request);
    const created = await startRegistryContainer({
      suffix: `port-${testInfo.workerIndex}-${testInfo.parallelIndex}`,
    });
    try {
      await replacePublishedTag(created.docker, 'alpine:3.21', created.image);
      const watch = await watchHostJobs(request, host.id);
      const checkRes = await request.post(
        `/api/containers/check/${host.id}/${created.name}`,
      );
      expect(checkRes.ok(), await checkRes.text()).toBeTruthy();
      const state = await watch.waitUntilSettled({ names: [created.name] });
      const item = jobResults(state, [created.name]).find(
        (result) => result.image_spec === created.image,
      );
      expect(['available', 'available(notified)']).toContain(item?.result);
    } finally {
      await created.cleanup();
    }
  });

  test('marks a digest-pinned image as not available when the tag moves', async ({
    authorizedRequest: request,
  }, testInfo) => {
    await allowLocalRegistry(request);
    const host = await getEnabledHost(request);
    const suffix = `digest-${testInfo.workerIndex}-${testInfo.parallelIndex}`;
    const published = await startRegistryContainer({
      suffix,
      create: false,
    });
    const pinned = await startRegistryContainer({
      suffix: `${suffix}-pin`,
      publish: false,
      imageRef: published.digest,
    });
    try {
      await replacePublishedTag(pinned.docker, 'alpine:3.21', published.image);
      const watch = await watchHostJobs(request, host.id);
      const checkRes = await request.post(
        `/api/containers/check/${host.id}/${pinned.name}`,
      );
      expect(checkRes.ok(), await checkRes.text()).toBeTruthy();
      const state = await watch.waitUntilSettled({ names: [pinned.name] });
      const item = jobResults(state, [pinned.name])[0];
      expect(item?.image_spec).toContain('@sha256:');
      expect(item?.result).toBe('not_available');
    } finally {
      await pinned.cleanup();
      await published.cleanup();
    }
  });

  test('checks a protected container and does not recreate it', async ({
    authorizedRequest: request,
  }, testInfo) => {
    await allowLocalRegistry(request);
    const host = await getEnabledHost(request);
    const docker = getDocker();
    const created = await startRegistryContainer({
      suffix: `protected-${testInfo.workerIndex}-${testInfo.parallelIndex}`,
      labels: { [PROTECTED_LABEL]: 'true' },
    });
    try {
      await replacePublishedTag(created.docker, 'alpine:3.21', created.image);
      const before = await docker.getContainer(created.name).inspect();

      const checkWatch = await watchHostJobs(request, host.id);
      const checkRes = await request.post(
        `/api/containers/check/${host.id}/${created.name}`,
      );
      expect(checkRes.ok(), await checkRes.text()).toBeTruthy();
      const checkState = await checkWatch.waitUntilSettled({
        names: [created.name],
      });
      const checked = jobResults(checkState, [created.name]).find(
        (result) => result.image_spec === created.image,
      );
      expect(['available', 'available(notified)']).toContain(checked?.result);

      const updateWatch = await watchHostJobs(request, host.id);
      const updateRes = await request.post(
        `/api/containers/update/${host.id}/${created.name}`,
      );
      expect(updateRes.ok(), await updateRes.text()).toBeTruthy();
      await updateWatch.waitUntilSettled({ names: [created.name] });

      const after = await docker.getContainer(created.name).inspect();
      expect(after.Id).toBe(before.Id);
      expect(after.State.Running).toBe(true);
      expect(after.Name).toBe(before.Name);
    } finally {
      await created.cleanup();
    }
  });
});
