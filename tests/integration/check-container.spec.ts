import { mergeTests, expect } from '@playwright/test';
import type { ContainerListItem } from '../shared/types/containers.types';
import { jobResults } from '../shared/types/jobs.types';
import { test as authTest } from '../fixtures/auth-request.fixture';
import { test as outdatedAlpineContainerTest } from '../fixtures/outdated-alpine-container.fixture';
import { getEnabledHost } from './hosts.util';
import { watchHostJobs } from './progress.util';

export const test = mergeTests(authTest, outdatedAlpineContainerTest);

test.describe('check container update availability', () => {
  test.setTimeout(120_000);

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
});
