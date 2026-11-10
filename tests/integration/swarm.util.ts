/* eslint-disable playwright/no-skipped-test -- specs skip when this engine is not a disposable Swarm manager */
import { expect, test, type APIRequestContext } from '@playwright/test';
import type Docker from 'dockerode';
import type { HostInfo } from '../shared/types/hosts.types';
import type { ServiceListItem } from '../shared/types/services.types';
import { getDocker } from '../shared/util/docker.util';
import { getEnabledHost } from './hosts.util';

const TEST_LABEL = 'dev.quenary.tugtainer.test';
const MONITOR_NS = 1_000_000_000;

export interface TestService {
  docker: Docker;
  id: string;
  name: string;
  image: string;
  cleanup: () => Promise<void>;
}

interface SwarmTask {
  Status?: { State?: string };
  Spec?: { ContainerSpec?: { Image?: string } };
}

export function digestPart(repoDigest: string): string {
  const at = repoDigest.lastIndexOf('@');
  return at === -1 ? repoDigest : repoDigest.slice(at + 1);
}

export function pinnedImage(image: string, repoDigest: string): string {
  return `${image}@${digestPart(repoDigest)}`;
}

/**
 * Refresh the host, then skip when Swarm was disabled or the agent is not a manager.
 */
export async function ensureSwarmHost(
  request: APIRequestContext,
): Promise<HostInfo> {
  test.skip(process.env.TUGTAINER_SWARM === '0', 'Swarm init failed');
  const host = await getEnabledHost(request);
  const status = await request.get(`/api/hosts/${host.id}/status`);
  expect(status.ok(), await status.text()).toBeTruthy();
  const body = (await status.json()) as { ok?: boolean; err?: string | null };
  expect(body.ok, body.err ?? 'host status failed').toBeTruthy();

  const hostsRes = await request.get('/api/hosts/list');
  expect(hostsRes.ok(), await hostsRes.text()).toBeTruthy();
  const hosts = (await hostsRes.json()) as HostInfo[];
  const refreshed = hosts.find((item) => item.id === host.id);
  test.skip(!refreshed?.is_swarm, 'Host is not a Swarm manager');
  return refreshed!;
}

/**
 * Global update touches every service and container that already has an update.
 * Skip that spec when this engine is not the disposable test stack.
 */
export async function skipUnlessTestEngine(docker: Docker): Promise<void> {
  let listed: Awaited<ReturnType<Docker['listServices']>>;
  try {
    listed = await docker.listServices();
  } catch {
    test.skip(true, 'Docker is not a Swarm manager');
    return;
  }
  const foreignServices = listed
    .filter((service) => service.Spec?.Labels?.[TEST_LABEL] !== 'swarm')
    .map((service) => service.Spec?.Name ?? service.ID);
  test.skip(
    foreignServices.length > 0,
    `Swarm has other services (${foreignServices.slice(0, 5).join(', ')}); global update is skipped`,
  );

  const containers = await docker.listContainers({ all: true });
  const unexpected = containers
    .filter((container) => {
      const labels = container.Labels ?? {};
      return (
        labels['dev.quenary.tugtainer.protected'] !== 'true' &&
        !labels[TEST_LABEL]
      );
    })
    .map((container) => container.Names?.[0] ?? container.Id);
  test.skip(
    unexpected.length > 0,
    `Engine has containers outside the test stack (${unexpected.slice(0, 5).join(', ')}); global update is skipped`,
  );
}

export async function createService(options: {
  suffix: string;
  image: string;
}): Promise<TestService> {
  const docker = getDocker();
  const name = `tug-swarm-${options.suffix}`.slice(0, 63);
  const created = await docker.createService({
    Name: name,
    Labels: { [TEST_LABEL]: 'swarm' },
    TaskTemplate: {
      ContainerSpec: {
        Image: options.image,
        Command: ['sleep', 'infinity'],
        Labels: { [TEST_LABEL]: 'swarm' },
      },
      RestartPolicy: { Condition: 'none' },
    },
    Mode: { Replicated: { Replicas: 1 } },
    UpdateConfig: {
      Parallelism: 1,
      Order: 'stop-first',
      FailureAction: 'pause',
      Monitor: MONITOR_NS,
    },
  });
  const info = await created.inspect();
  const id = info.ID;
  return {
    docker,
    id,
    name,
    image: options.image,
    cleanup: async () => {
      try {
        await docker.getService(id).remove();
      } catch (err) {
        const statusCode = (err as { statusCode?: number }).statusCode;
        if (statusCode !== 404) {
          throw err;
        }
      }
    },
  };
}

export async function serviceImage(
  docker: Docker,
  id: string,
): Promise<string> {
  const info = await docker.getService(id).inspect();
  const template = info.Spec?.TaskTemplate;
  if (!template || !('ContainerSpec' in template)) {
    return '';
  }
  return template.ContainerSpec?.Image ?? '';
}

export async function waitServiceRunning(
  docker: Docker,
  name: string,
): Promise<void> {
  await expect
    .poll(
      async () => {
        const tasks = (await docker.listTasks({
          filters: { service: [name] },
        })) as SwarmTask[];
        return tasks.some((task) => task.Status?.State === 'running');
      },
      { timeout: 90_000, intervals: [500, 1000, 2000] },
    )
    .toBe(true);
}

/**
 * Poll until the spec image and a running task carry `digest`.
 * A rollback state fails the poll. An empty update status is a create that
 * never went through a service update.
 */
export async function waitServiceConverged(
  docker: Docker,
  id: string,
  name: string,
  digest: string,
  options?: { requireCompleted?: boolean },
): Promise<void> {
  await expect
    .poll(
      async () => {
        const info = await docker.getService(id).inspect();
        const template = info.Spec?.TaskTemplate;
        const image =
          template && 'ContainerSpec' in template
            ? (template.ContainerSpec?.Image ?? '')
            : '';
        const state = info.UpdateStatus?.State ?? '';
        if (state.includes('rollback')) {
          return `rollback:${state}`;
        }
        const tasks = (await docker.listTasks({
          filters: { service: [name] },
        })) as SwarmTask[];
        const runningOnDigest = tasks.some(
          (task) =>
            task.Status?.State === 'running' &&
            (task.Spec?.ContainerSpec?.Image ?? '').includes(digest),
        );
        const statusOk = options?.requireCompleted
          ? state === 'completed'
          : state === '' || state === 'completed';
        if (image.includes(digest) && runningOnDigest && statusOk) {
          return 'ok';
        }
        return state || 'pending';
      },
      { timeout: 90_000, intervals: [1000, 2000] },
    )
    .toBe('ok');
}

export async function listServices(
  request: APIRequestContext,
  hostId: number,
): Promise<ServiceListItem[]> {
  const response = await request.get(`/api/hosts/${hostId}/services`);
  expect(response.ok(), await response.text()).toBeTruthy();
  return (await response.json()) as ServiceListItem[];
}

export async function patchService(
  request: APIRequestContext,
  hostId: number,
  name: string,
  body: { check_enabled?: boolean; update_enabled?: boolean },
): Promise<void> {
  const response = await request.patch(
    `/api/hosts/${hostId}/services/${encodeURIComponent(name)}`,
    { data: body },
  );
  expect(response.ok(), await response.text()).toBeTruthy();
}

export async function checkServices(
  request: APIRequestContext,
  hostId: number,
  names: string[],
): Promise<void> {
  const response = await request.post(`/api/hosts/${hostId}/services/check`, {
    data: { names },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
}

export async function updateServices(
  request: APIRequestContext,
  hostId: number,
  names: string[],
): Promise<void> {
  const response = await request.post(`/api/hosts/${hostId}/services/update`, {
    data: { names },
  });
  expect(response.ok(), await response.text()).toBeTruthy();
}
