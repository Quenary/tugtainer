import { expect, type APIRequestContext } from '@playwright/test';

export const LOCAL_REGISTRY = 'localhost:5000';

/** Open registry plus the private and unauthorized registries used in tests. */
export const LOCAL_REGISTRIES = [
  'localhost:5000',
  'localhost:5001',
  'localhost:5002',
].join('\n');

export async function patchSetting(
  request: APIRequestContext,
  key: string,
  value: boolean | number | string,
): Promise<void> {
  const response = await request.patch('/api/settings/change', {
    data: [{ key, value }],
  });
  expect(response.ok(), await response.text()).toBeTruthy();
}

/**
 * HTTP registries are refused until their host is listed. Tests share this
 * value and leave it in place: clearing it from one test would race another.
 * Hub checks stay on HTTPS and are unaffected. `test:all` drops the database.
 */
export async function allowLocalRegistry(
  request: APIRequestContext,
): Promise<void> {
  await patchSetting(request, 'INSECURE_REGISTRIES', LOCAL_REGISTRIES);
}
