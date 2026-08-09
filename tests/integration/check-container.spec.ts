import { mergeTests, expect, type APIRequestContext } from '@playwright/test';
import type {
  ContainerActionProgress,
  ContainerListItem,
} from '../shared/types/containers.types';
import type { HostInfo } from '../shared/types/hosts.types';
import { test as authTest } from '../fixtures/auth-request.fixture';
import { test as outdatedAlpineContainerTest } from '../fixtures/outdated-alpine-container.fixture';

export const test = mergeTests(authTest, outdatedAlpineContainerTest);

async function getProgress(
  request: APIRequestContext,
  cacheId: string,
): Promise<ContainerActionProgress | null> {
  const response = await request.get('/api/containers/progress', {
    params: { cache_id: cacheId },
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as ContainerActionProgress | null;
}

function assertProgress(
  progress: ContainerActionProgress | null,
): asserts progress is ContainerActionProgress {
  expect(progress, 'expected progress to exist').not.toBeNull();
}

test.describe('check container update availability', () => {
  test.setTimeout(120_000);

  test('marks container with outdated image as available', async ({
    authorizedRequest: request,
    outdatedAlpineContainer,
  }) => {
    const hostsRes = await request.get('/api/hosts/list');
    expect(hostsRes.ok()).toBeTruthy();
    const hosts = (await hostsRes.json()) as HostInfo[];
    const host = hosts.find((h) => h.enabled);
    expect(host, 'expected an enabled docker host').toBeTruthy();

    const checkRes = await request.post(
      `/api/containers/check/${host!.id}/${outdatedAlpineContainer.name}`,
    );
    expect(checkRes.ok()).toBeTruthy();
    const cacheId = (await checkRes.json()) as string;
    expect(cacheId).toBeTruthy();

    await expect
      .poll(
        async () => {
          const progress = await getProgress(request, cacheId);
          return progress?.status ?? null;
        },
        {
          timeout: 90_000,
          intervals: [500, 1000, 2000],
        },
      )
      .toMatch(/^(DONE|ERROR)$/);

    const progress = await getProgress(request, cacheId);
    assertProgress(progress);

    expect(progress.status).toBe('DONE');
    // "available(notified)" is the same verdict for a re-check of a digest
    // already stored in the db (e.g. app volume kept between runs)
    expect(['available', 'available(notified)']).toContain(
      progress.result?.result,
    );
    expect(progress.result?.image_spec).toBe(outdatedAlpineContainer.image);

    const listRes = await request.get(`/api/containers/${host!.id}/list`);
    expect(listRes.ok()).toBeTruthy();
    const list = (await listRes.json()) as ContainerListItem[];
    const item = list.find((c) => c.name === outdatedAlpineContainer.name);
    expect(item?.update_available).toBe(true);
  });
});
