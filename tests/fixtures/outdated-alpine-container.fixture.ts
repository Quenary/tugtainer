import { test as base } from '@playwright/test';
import {
  getDocker,
  pullImage,
  removeContainerIfExists,
  removeImageTagIfExists,
} from '../shared/util/docker.util';

/** Real older image used as the container's local layers. */
export const SOURCE_IMAGE = 'alpine:3.22';
/**
 * Tag that exists on Docker Hub with a newer digest.
 * Locally we retag SOURCE_IMAGE as this so the check sees an update.
 */
export const STALE_TAG = 'alpine:3.23';
export const TEST_CONTAINER_NAME = 'tugtainer-test-check-updates';

export interface OutdatedAlpineContainer {
  name: string;
  image: string;
}

/**
 * Pulls alpine:3.22, tags it as alpine:3.23 (stale for that tag), starts a
 * container from that tag, and cleans up after the test.
 */
export const test = base.extend<{
  outdatedAlpineContainer: OutdatedAlpineContainer;
}>({
  // Playwright requires a destructuring pattern for the fixtures argument
  // eslint-disable-next-line no-empty-pattern
  outdatedAlpineContainer: async ({}, use, testInfo) => {
    const docker = getDocker();
    const name = `${TEST_CONTAINER_NAME}-${testInfo.workerIndex}-${testInfo.parallelIndex}`;

    await removeContainerIfExists(docker, name);
    await removeImageTagIfExists(docker, STALE_TAG);

    await pullImage(docker, SOURCE_IMAGE);

    const [repo, tag] = STALE_TAG.split(':') as [string, string];
    await docker.getImage(SOURCE_IMAGE).tag({ repo, tag });

    const container = await docker.createContainer({
      Image: STALE_TAG,
      name,
      Cmd: ['sleep', 'infinity'],
      Labels: {
        'dev.quenary.tugtainer.test': 'check-updates',
      },
    });
    await container.start();

    try {
      await use({ name, image: STALE_TAG });
    } finally {
      await removeContainerIfExists(docker, name);
      await removeImageTagIfExists(docker, STALE_TAG);
    }
  },
});
