import { test as base } from '@playwright/test';
import {
  connectContainerToNetwork,
  getDocker,
  pullImage,
  removeContainerIfExists,
  removeImageTagIfExists,
  removeNetworkIfExists,
} from '../shared/util/docker.util';

/** Distinct from check-container's 3.22/3.23 pair so the tests can run in parallel. */
export const SOURCE_IMAGE = 'alpine:3.20';
export const STALE_TAG = 'alpine:3.21';

export const APP_NAME = 'tugtainer-test-update-app';
export const DB_NAME = 'tugtainer-test-update-db';
export const PRIMARY_NET = 'tugtainer-test-update-primary';
export const EXTRA_NET = 'tugtainer-test-update-extra';
export const EXTRA_ALIAS = 'app';
export const LINK_ALIAS = 'db';

const TEST_LABEL = 'update-extra-network';

export interface OutdatedAlpineExtraNetwork {
  name: string;
  image: string;
  extraNetwork: string;
  primaryNetwork: string;
  extraAlias: string;
  linkTargetName: string;
  linkAlias: string;
}

async function cleanup(): Promise<void> {
  const docker = getDocker();
  await removeContainerIfExists(docker, APP_NAME);
  await removeContainerIfExists(docker, DB_NAME);
  await removeNetworkIfExists(docker, EXTRA_NET);
  await removeNetworkIfExists(docker, PRIMARY_NET);
  await removeImageTagIfExists(docker, STALE_TAG);
}

/**
 * Outdated alpine container on a primary user-defined network, plus a second
 * network connected with alias + --link (the path that failed in #225).
 */
export const test = base.extend<{
  outdatedAlpineExtraNetwork: OutdatedAlpineExtraNetwork;
}>({
  // Playwright requires a destructuring pattern for the fixtures argument
  // eslint-disable-next-line no-empty-pattern
  outdatedAlpineExtraNetwork: async ({}, use) => {
    const docker = getDocker();
    await cleanup();

    try {
      await pullImage(docker, SOURCE_IMAGE);

      const [repo, tag] = STALE_TAG.split(':') as [string, string];
      await docker.getImage(SOURCE_IMAGE).tag({ repo, tag });

      await docker.createNetwork({
        Name: EXTRA_NET,
        CheckDuplicate: true,
        Labels: { 'dev.quenary.tugtainer.test': TEST_LABEL },
      });
      await docker.createNetwork({
        Name: PRIMARY_NET,
        CheckDuplicate: true,
        Labels: { 'dev.quenary.tugtainer.test': TEST_LABEL },
      });

      const db = await docker.createContainer({
        Image: SOURCE_IMAGE,
        name: DB_NAME,
        Cmd: ['sleep', 'infinity'],
        Labels: { 'dev.quenary.tugtainer.test': TEST_LABEL },
        HostConfig: { NetworkMode: EXTRA_NET },
      });
      await db.start();

      const app = await docker.createContainer({
        Image: STALE_TAG,
        name: APP_NAME,
        Cmd: ['sleep', 'infinity'],
        Labels: { 'dev.quenary.tugtainer.test': TEST_LABEL },
        HostConfig: { NetworkMode: PRIMARY_NET },
      });
      await app.start();
      await connectContainerToNetwork(docker, EXTRA_NET, APP_NAME, {
        aliases: [EXTRA_ALIAS],
        links: [`${DB_NAME}:${LINK_ALIAS}`],
      });

      await use({
        name: APP_NAME,
        image: STALE_TAG,
        extraNetwork: EXTRA_NET,
        primaryNetwork: PRIMARY_NET,
        extraAlias: EXTRA_ALIAS,
        linkTargetName: DB_NAME,
        linkAlias: LINK_ALIAS,
      });
    } finally {
      await cleanup();
    }
  },
});
