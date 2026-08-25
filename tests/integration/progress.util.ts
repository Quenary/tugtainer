import { expect, type APIRequestContext } from '@playwright/test';
import type { ActionProgress } from '../shared/types/progress.types';

export async function getProgress<T extends ActionProgress>(
  request: APIRequestContext,
  cacheId: string,
): Promise<T | null> {
  const response = await request.get('/api/containers/progress', {
    params: { cache_id: cacheId },
  });
  expect(response.ok()).toBeTruthy();
  return (await response.json()) as T | null;
}

export async function waitUntilSettled<T extends ActionProgress>(
  request: APIRequestContext,
  cacheId: string,
): Promise<T> {
  await expect
    .poll(
      async () => {
        const progress = await getProgress<T>(request, cacheId);
        return progress?.status ?? null;
      },
      {
        timeout: 90_000,
        intervals: [500, 1000, 2000],
      },
    )
    .toMatch(/^(DONE|ERROR)$/);

  const progress = await getProgress<T>(request, cacheId);
  expect(progress, 'expected progress to exist').not.toBeNull();
  expect(progress!.status).toBe('DONE');
  return progress!;
}
