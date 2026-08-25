import { expect, type APIRequestContext } from '@playwright/test';
import type { HostInfo } from '../shared/types/hosts.types';

export async function getEnabledHost(
  request: APIRequestContext,
): Promise<HostInfo> {
  const hostsRes = await request.get('/api/hosts/list');
  expect(hostsRes.ok()).toBeTruthy();
  const hosts = (await hostsRes.json()) as HostInfo[];
  const host = hosts.find((h) => h.enabled);
  expect(host, 'expected an enabled docker host').toBeTruthy();
  return host!;
}
