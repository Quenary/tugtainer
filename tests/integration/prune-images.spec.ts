import { expect, type APIRequestContext } from '@playwright/test';
import type Docker from 'dockerode';
import { test } from '../fixtures/auth-request.fixture';
import {
  getDocker,
  pullImage,
  removeImageTagIfExists,
} from '../shared/util/docker.util';
import { getEnabledHost } from './hosts.util';

const LABEL_KEY = 'dev.quenary.tugtainer.prune';

test.describe('image prune', () => {
  test.setTimeout(180_000);

  test('prune_all removes tagged unused images and formats the result', async ({
    authorizedRequest: request,
  }, testInfo) => {
    const host = await getEnabledHost(request);
    const docker = getDocker();
    const suffix = `${testInfo.workerIndex}-${testInfo.parallelIndex}-${Date.now()}`;
    const label = `${LABEL_KEY}=${suffix}`;
    const repo = `tugtainer-test-prune-${suffix}`;
    const tag = 'app';
    const tagged = `${repo}:${tag}`;
    await pullImage(docker, 'alpine:3.20');
    let danglingId = '';
    let taggedId = '';
    try {
      danglingId = await commitLabeled(docker, repo, tag, label, 'first');
      taggedId = await commitLabeled(docker, repo, tag, label, 'second');
      expect(danglingId).not.toBe(taggedId);
      expect(await imageTags(docker, danglingId)).not.toContain(tagged);
      expect(await imageTags(docker, taggedId)).toContain(tagged);

      const danglingOnly = await prune(request, host.id, false, label);
      expectPruneText(danglingOnly);
      expect(await imageExists(docker, danglingId)).toBe(false);
      expect(await imageExists(docker, taggedId)).toBe(true);

      const all = await prune(request, host.id, true, label);
      expectPruneText(all);
      expect(await imageExists(docker, taggedId)).toBe(false);
    } finally {
      await removeImageTagIfExists(docker, tagged);
      await removeImageIfPresent(docker, danglingId);
      await removeImageIfPresent(docker, taggedId);
    }
  });
});

async function commitLabeled(
  docker: Docker,
  repo: string,
  tag: string,
  label: string,
  generation: string,
): Promise<string> {
  const builder = await docker.createContainer({
    Image: 'alpine:3.20',
    Cmd: ['/bin/true'],
  });
  try {
    await builder.start();
    await builder.wait();
    const committed = await builder.commit({
      repo,
      tag,
      changes: [
        `LABEL ${label}`,
        `LABEL ${LABEL_KEY}.generation=${generation}`,
      ],
    });
    return committed.Id;
  } finally {
    await builder.remove({ force: true });
  }
}

async function prune(
  request: APIRequestContext,
  hostId: number,
  all: boolean,
  label: string,
): Promise<string> {
  const response = await request.post(`/api/images/${hostId}/prune`, {
    data: { all, filters: { label: [label] } },
  });
  const raw = await response.text();
  expect(response.ok(), raw).toBeTruthy();
  return JSON.parse(raw) as string;
}

function expectPruneText(text: string): void {
  expect(text).toContain('Deleted Images:');
  expect(text).toContain('Untagged Images:');
  const lines = text.trim().split('\n');
  expect(lines[lines.length - 1]).toMatch(/^Total reclaimed space: /);
}

async function imageTags(docker: Docker, id: string): Promise<string[]> {
  const info = await docker.getImage(id).inspect();
  return info.RepoTags ?? [];
}

async function removeImageIfPresent(docker: Docker, id: string): Promise<void> {
  if (!id) {
    return;
  }
  await removeImageTagIfExists(docker, id);
}

async function imageExists(docker: Docker, id: string): Promise<boolean> {
  try {
    await docker.getImage(id).inspect();
    return true;
  } catch (err) {
    const statusCode = (err as { statusCode?: number }).statusCode;
    if (statusCode === 404) {
      return false;
    }
    throw err;
  }
}
