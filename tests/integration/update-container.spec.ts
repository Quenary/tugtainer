import { mergeTests, expect } from '@playwright/test';
import { jobResults } from '../shared/types/jobs.types';
import { test as authTest } from '../fixtures/auth-request.fixture';
import { test as outdatedAlpineExtraNetworkTest } from '../fixtures/outdated-alpine-extra-network.fixture';
import { getDocker } from '../shared/util/docker.util';
import { getEnabledHost } from './hosts.util';
import { getHostState, watchHostJobs } from './progress.util';

export const test = mergeTests(authTest, outdatedAlpineExtraNetworkTest);

interface NetworkEndpoint {
  Aliases?: string[] | null;
  Links?: string[] | null;
}

function extraEndpoint(
  networks: Record<string, NetworkEndpoint> | undefined,
  extraNetwork: string,
): NetworkEndpoint {
  expect(networks, 'expected network attachments').toBeTruthy();
  const endpoint = networks![extraNetwork];
  expect(endpoint, `expected attachment to ${extraNetwork}`).toBeTruthy();
  return endpoint;
}

test.describe('update container with extra network', () => {
  test.setTimeout(240_000);

  test('recreates container and reconnects extra network with alias and link', async ({
    authorizedRequest: request,
    outdatedAlpineExtraNetwork,
  }) => {
    const host = await getEnabledHost(request);

    const docker = getDocker();
    const before = await docker
      .getContainer(outdatedAlpineExtraNetwork.name)
      .inspect();
    const beforeEndpoint = extraEndpoint(
      before.NetworkSettings.Networks as Record<string, NetworkEndpoint>,
      outdatedAlpineExtraNetwork.extraNetwork,
    );
    expect(beforeEndpoint.Aliases).toEqual(
      expect.arrayContaining([outdatedAlpineExtraNetwork.extraAlias]),
    );
    expect(beforeEndpoint.Links).toEqual(
      expect.arrayContaining([
        `${outdatedAlpineExtraNetwork.linkTargetName}:${outdatedAlpineExtraNetwork.linkAlias}`,
      ]),
    );

    const names = [outdatedAlpineExtraNetwork.name];
    const checkWatch = await watchHostJobs(request, host.id);
    const checkRes = await request.post(
      `/api/containers/check/${host.id}/${outdatedAlpineExtraNetwork.name}`,
    );
    expect(checkRes.ok()).toBeTruthy();
    const checkState = await checkWatch.waitUntilSettled({ names });
    expect(['available', 'available(notified)']).toContain(
      jobResults(checkState, names)[0]?.result,
    );

    const updateRes = await request.post(
      `/api/containers/update/${host.id}/${outdatedAlpineExtraNetwork.name}`,
    );
    expect(updateRes.ok()).toBeTruthy();
    await expect
      .poll(
        async () => {
          const state = await getHostState(request, host.id);
          return (
            jobResults(state, names).some(
              (item) => item.result === 'updated',
            ) ?? false
          );
        },
        {
          timeout: 240_000,
          intervals: [500, 1000, 2000],
        },
      )
      .toBe(true);

    const after = await docker
      .getContainer(outdatedAlpineExtraNetwork.name)
      .inspect();
    expect(after.State.Running).toBe(true);
    expect(after.Image).not.toBe(before.Image);
    expect(after.Config.Image).toBe(outdatedAlpineExtraNetwork.image);
    expect(after.NetworkSettings.Networks).toHaveProperty(
      outdatedAlpineExtraNetwork.primaryNetwork,
    );

    const afterEndpoint = extraEndpoint(
      after.NetworkSettings.Networks as Record<string, NetworkEndpoint>,
      outdatedAlpineExtraNetwork.extraNetwork,
    );
    expect(afterEndpoint.Aliases).toEqual(
      expect.arrayContaining([outdatedAlpineExtraNetwork.extraAlias]),
    );
    expect(afterEndpoint.Links).toEqual(
      expect.arrayContaining([
        `${outdatedAlpineExtraNetwork.linkTargetName}:${outdatedAlpineExtraNetwork.linkAlias}`,
      ]),
    );
  });
});
