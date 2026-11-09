import { mergeTests, expect, type APIRequestContext } from '@playwright/test';
import { jobResults, type HostState } from '../shared/types/jobs.types';
import { test as authTest } from '../fixtures/auth-request.fixture';
import { test as outdatedAlpineExtraNetworkTest } from '../fixtures/outdated-alpine-extra-network.fixture';
import {
  pickHostMounts,
  pickPreservedConfig,
  preservedHostMounts,
} from '../shared/util/container-config.util';
import {
  execInContainer,
  getDocker,
  removeContainerIfExists,
  removeImageTagIfExists,
} from '../shared/util/docker.util';
import {
  imageName,
  publishFailingHealthcheck,
  publishImageHealthcheck,
  replacePublishedTag,
} from '../shared/util/registry.util';
import { getEnabledHost } from './hosts.util';
import { getHostState, watchHostJobs } from './progress.util';
import { startRegistryContainer } from './registry-container.util';
import { allowLocalRegistry, patchSetting } from './settings.util';

export const test = mergeTests(authTest, outdatedAlpineExtraNetworkTest);

// One host runs a single job at a time. Parallel updates queue behind each
// other and the settle wait expires before the later jobs start.
test.describe.configure({ mode: 'serial' });

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

async function checkAvailable(
  request: APIRequestContext,
  hostId: number,
  name: string,
  image: string,
): Promise<void> {
  const watch = await watchHostJobs(request, hostId);
  const checkRes = await request.post(
    `/api/containers/check/${hostId}/${name}`,
  );
  expect(checkRes.ok(), await checkRes.text()).toBeTruthy();
  const state = await watch.waitUntilSettled({ names: [name] });
  const item = jobResults(state, [name]).find(
    (result) => result.image_spec === image,
  );
  expect(['available', 'available(notified)']).toContain(item?.result);
}

async function waitForResult(
  request: APIRequestContext,
  hostId: number,
  name: string,
  result: string,
): Promise<HostState> {
  let settled: HostState | null = null;
  await expect
    .poll(
      async () => {
        settled = await getHostState(request, hostId);
        return (
          jobResults(settled, [name]).some((item) => item.result === result) ??
          false
        );
      },
      { timeout: 240_000, intervals: [500, 1000, 2000] },
    )
    .toBe(true);
  return settled!;
}

test.describe('update container with extra network', () => {
  test.setTimeout(240_000);

  test('recreates container and keeps host, network, and volume config', async ({
    authorizedRequest: request,
    outdatedAlpineExtraNetwork,
  }) => {
    const host = await getEnabledHost(request);
    const docker = getDocker();
    const container = outdatedAlpineExtraNetwork;
    const before = await docker.getContainer(container.name).inspect();
    const beforeImage = await docker.getImage(before.Image).inspect();
    const beforeEndpoint = extraEndpoint(
      before.NetworkSettings.Networks as Record<string, NetworkEndpoint>,
      container.extraNetwork,
    );
    expect(beforeEndpoint.Aliases).toEqual(
      expect.arrayContaining([container.extraAlias]),
    );
    expect(beforeEndpoint.Links).toEqual(
      expect.arrayContaining([
        `${container.linkTargetName}:${container.linkAlias}`,
      ]),
    );
    expect(before.HostConfig.ExtraHosts).toEqual(
      expect.arrayContaining([
        'host.docker.internal:host-gateway',
        'test.local:127.0.0.1',
      ]),
    );
    expect(before.HostConfig.Binds).toEqual(
      expect.arrayContaining([expect.stringContaining(':/bind:ro,z')]),
    );
    expect(before.Config.Healthcheck?.Test).toEqual(['CMD', 'true']);
    expect(pickHostMounts(before).map((mount) => mount.target)).toEqual(
      expect.arrayContaining(['/mount', '/mnt/bind', '/mnt/tmpfs', '/anon']),
    );
    await execInContainer(docker, container.name, [
      'sh',
      '-c',
      `echo preserved > ${container.dataPath} && echo preserved > ${container.anonPath}`,
    ]);

    await checkAvailable(request, host.id, container.name, container.image);

    const updateRes = await request.post(
      `/api/containers/update/${host.id}/${container.name}`,
    );
    expect(updateRes.ok(), await updateRes.text()).toBeTruthy();
    await waitForResult(request, host.id, container.name, 'updated');

    const after = await docker.getContainer(container.name).inspect();
    const afterImage = await docker.getImage(after.Image).inspect();
    expect(after.State.Running).toBe(true);
    expect(after.State.Health?.Status).toBe('healthy');
    expect(after.Id).not.toBe(before.Id);
    expect(after.Image).not.toBe(before.Image);
    expect(after.Name).toBe(before.Name);
    expect(pickPreservedConfig(after)).toEqual(pickPreservedConfig(before));
    expect(after.Config.Labels?.[container.userLabel]).toBe('yes');
    const droppedImageLabels = Object.keys(
      beforeImage.Config.Labels ?? {},
    ).filter((key) => !(key in (afterImage.Config.Labels ?? {})));
    expect(
      droppedImageLabels.filter(
        (key) => after.Config.Labels?.[key] !== undefined,
      ),
    ).toEqual([]);
    expect(after.HostConfig.PortBindings?.['8080/tcp']).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          HostIp: '127.0.0.1',
          HostPort: container.publishedPort,
        }),
      ]),
    );
    const afterEndpoint = extraEndpoint(
      after.NetworkSettings.Networks as Record<string, NetworkEndpoint>,
      container.extraNetwork,
    );
    expect(afterEndpoint.Aliases).toEqual(
      expect.arrayContaining([container.extraAlias]),
    );
    expect(afterEndpoint.Links).toEqual(
      expect.arrayContaining([
        `${container.linkTargetName}:${container.linkAlias}`,
      ]),
    );
    expect(after.HostConfig.ExtraHosts).toEqual(
      expect.arrayContaining([
        'host.docker.internal:host-gateway',
        'test.local:127.0.0.1',
      ]),
    );
    expect(after.HostConfig.Binds).toEqual(before.HostConfig.Binds);
    expect(after.Config.Healthcheck?.Test).toEqual(['CMD', 'true']);
    // Anonymous volumes gain a source id when they are reattached.
    expect(preservedHostMounts(after, before)).toEqual(pickHostMounts(before));
    const primary = after.NetworkSettings.Networks?.[
      container.primaryNetwork
    ] as { GwPriority?: number } | undefined;
    expect(primary?.GwPriority ?? null).toBe(container.gatewayPriority);
    const data = await execInContainer(docker, container.name, [
      'sh',
      '-c',
      `cat ${container.dataPath} ${container.anonPath}`,
    ]);
    expect(data).toContain('preserved');
  });
});

test.describe('update edge cases', () => {
  test.setTimeout(240_000);

  test('updates a stopped container without starting it', async ({
    authorizedRequest: request,
  }, testInfo) => {
    await allowLocalRegistry(request);
    const host = await getEnabledHost(request);
    const created = await startRegistryContainer({
      suffix: `stopped-${testInfo.workerIndex}-${testInfo.parallelIndex}`,
      start: false,
      volume: true,
    });
    try {
      await replacePublishedTag(created.docker, 'alpine:3.21', created.image);
      const before = await created.docker.getContainer(created.name).inspect();
      expect(before.State.Running).toBe(false);

      await checkAvailable(request, host.id, created.name, created.image);
      await patchSetting(request, 'UPDATE_ONLY_RUNNING', false);
      const updateRes = await request.post(
        `/api/containers/update/${host.id}/${created.name}`,
      );
      expect(updateRes.ok(), await updateRes.text()).toBeTruthy();
      await waitForResult(request, host.id, created.name, 'updated');

      const after = await created.docker.getContainer(created.name).inspect();
      expect(after.State.Running).toBe(false);
      expect(after.Id).not.toBe(before.Id);
      expect(after.Name).toBe(before.Name);
      expect(pickPreservedConfig(after)).toEqual(pickPreservedConfig(before));
    } finally {
      await patchSetting(request, 'UPDATE_ONLY_RUNNING', true);
      await created.cleanup();
    }
  });

  test('leaves the original container running when recreate is refused', async ({
    authorizedRequest: request,
  }, testInfo) => {
    await allowLocalRegistry(request);
    const host = await getEnabledHost(request);
    const suffix = `preflight-${testInfo.workerIndex}-${testInfo.parallelIndex}`;
    const created = await startRegistryContainer({
      suffix,
      cidfile: `/tmp/tugtainer-${suffix}.cid`,
    });
    try {
      await replacePublishedTag(created.docker, 'alpine:3.21', created.image);
      const before = await created.docker.getContainer(created.name).inspect();
      await checkAvailable(request, host.id, created.name, created.image);

      const watch = await watchHostJobs(request, host.id);
      const updateRes = await request.post(
        `/api/containers/update/${host.id}/${created.name}`,
      );
      expect(updateRes.ok(), await updateRes.text()).toBeTruthy();
      const state = await watch.waitUntilSettled({ names: [created.name] });
      const item = jobResults(state, [created.name])[0];
      expect(item?.result ?? null).not.toBe('updated');
      expect(item?.error ?? '').toContain('uses cidfile');

      const after = await created.docker.getContainer(created.name).inspect();
      expect(after.Id).toBe(before.Id);
      expect(after.State.Running).toBe(true);
      expect(after.Name).toBe(before.Name);
    } finally {
      await created.cleanup();
    }
  });

  test('adopts the new image healthcheck when the container did not override it', async ({
    authorizedRequest: request,
  }, testInfo) => {
    await allowLocalRegistry(request);
    const host = await getEnabledHost(request);
    const suffix = `inherit-${testInfo.workerIndex}-${testInfo.parallelIndex}`;
    const image = imageName(`tugtainer-test/${suffix}`, 'app');
    const name = `tugtainer-test-${suffix}`;
    const docker = getDocker();
    const inherited =
      'HEALTHCHECK --interval=1s --timeout=1s --retries=3 CMD ["true"]';
    const replacement =
      'HEALTHCHECK --interval=1s --timeout=1s --retries=3 CMD ["echo","updated"]';
    await publishImageHealthcheck(docker, 'alpine:3.20', image, inherited);
    let previousId: string | null = null;
    try {
      const created = await docker.createContainer({
        Image: image,
        name,
        Labels: { 'dev.quenary.tugtainer.test': 'inherit-healthcheck' },
      });
      await created.start();
      const before = await created.inspect();
      previousId = before.Image;
      expect(before.Config.Healthcheck?.Test).toEqual(['CMD', 'true']);

      await publishImageHealthcheck(docker, 'alpine:3.20', image, replacement, {
        dropLocal: true,
      });
      await checkAvailable(request, host.id, name, image);
      const updateRes = await request.post(
        `/api/containers/update/${host.id}/${name}`,
      );
      expect(updateRes.ok(), await updateRes.text()).toBeTruthy();
      await waitForResult(request, host.id, name, 'updated');

      const after = await docker.getContainer(name).inspect();
      expect(after.Id).not.toBe(before.Id);
      expect(after.State.Running).toBe(true);
      expect(after.Config.Healthcheck?.Test).toEqual([
        'CMD',
        'echo',
        'updated',
      ]);
    } finally {
      await removeContainerIfExists(docker, name);
      await removeImageTagIfExists(docker, image);
      await removeImageTagIfExists(docker, previousId ?? image);
    }
  });

  test('rolls back when the new image never becomes healthy', async ({
    authorizedRequest: request,
  }, testInfo) => {
    await allowLocalRegistry(request);
    const host = await getEnabledHost(request);
    const created = await startRegistryContainer({
      suffix: `rollback-${testInfo.workerIndex}-${testInfo.parallelIndex}`,
      volume: true,
    });
    try {
      await execInContainer(created.docker, created.name, [
        'sh',
        '-c',
        'echo preserved > /data/marker',
      ]);
      const before = await created.docker.getContainer(created.name).inspect();
      await publishFailingHealthcheck(
        created.docker,
        'alpine:3.20',
        created.image,
      );
      await checkAvailable(request, host.id, created.name, created.image);
      const timeoutRes = await request.patch(
        `/api/containers/${host.id}/${created.name}`,
        { data: { healthcheck_timeout: 15 } },
      );
      expect(timeoutRes.ok(), await timeoutRes.text()).toBeTruthy();

      const updateRes = await request.post(
        `/api/containers/update/${host.id}/${created.name}`,
      );
      expect(updateRes.ok(), await updateRes.text()).toBeTruthy();
      await waitForResult(request, host.id, created.name, 'rolled_back');

      const after = await created.docker.getContainer(created.name).inspect();
      expect(after.State.Running).toBe(true);
      expect(after.Name).toBe(before.Name);
      expect(after.State.Health?.Status ?? 'none').not.toBe('unhealthy');
      expect(pickPreservedConfig(after)).toEqual(pickPreservedConfig(before));
      const data = await execInContainer(created.docker, created.name, [
        'cat',
        '/data/marker',
      ]);
      expect(data).toContain('preserved');
    } finally {
      await created.cleanup();
    }
  });
});
