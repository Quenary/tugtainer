import { mergeTests, expect } from '@playwright/test';
import type {
  ContainerActionProgress,
  ContainerListItem,
} from '../shared/types/containers.types';
import { test as authTest } from '../fixtures/auth-request.fixture';
import { test as outdatedAlpineContainerTest } from '../fixtures/outdated-alpine-container.fixture';
import { getEnabledHost } from './hosts.util';
import { waitUntilSettled } from './progress.util';

export const test = mergeTests(authTest, outdatedAlpineContainerTest);

test.describe('check container update availability', () => {
  test.setTimeout(120_000);

  test('marks container with outdated image as available', async ({
    authorizedRequest: request,
    outdatedAlpineContainer,
  }) => {
    const host = await getEnabledHost(request);

    const checkRes = await request.post(
      `/api/containers/check/${host.id}/${outdatedAlpineContainer.name}`,
    );
    expect(checkRes.ok()).toBeTruthy();
    const cacheId = (await checkRes.json()) as string;
    expect(cacheId).toBeTruthy();

    const progress = await waitUntilSettled<ContainerActionProgress>(
      request,
      cacheId,
    );

    // "available(notified)" is the same verdict for a re-check of a digest
    // already stored in the db (e.g. app volume kept between runs)
    expect(['available', 'available(notified)']).toContain(
      progress.result?.result,
    );
    expect(progress.result?.image_spec).toBe(outdatedAlpineContainer.image);

    const listRes = await request.get(`/api/containers/${host.id}/list`);
    expect(listRes.ok()).toBeTruthy();
    const list = (await listRes.json()) as ContainerListItem[];
    const item = list.find((c) => c.name === outdatedAlpineContainer.name);
    expect(item?.update_available).toBe(true);
  });
});
