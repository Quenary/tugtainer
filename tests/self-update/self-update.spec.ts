import { expect, type APIRequestContext } from '@playwright/test';
import type Docker from 'dockerode';
import { login, test } from '../fixtures/auth-request.fixture';
import { getDocker } from '../shared/util/docker.util';

const APP_CONTAINER = 'tests-tugtainer';
const APP_IMAGE = 'localhost:5000/tugtainer:tests';
const NEXT_VERSION = 'tests-next';
const FINAL_STATUSES = [
  'succeeded',
  'aborted',
  'rolled_back',
  'failed',
  'interrupted',
];

async function followStream(
  docker: Docker,
  stream: NodeJS.ReadableStream,
): Promise<void> {
  await new Promise<void>((resolve, reject) => {
    docker.modem.followProgress(
      stream,
      (err) => (err ? reject(err) : resolve()),
      (event: { error?: string }) => {
        if (event.error) {
          reject(new Error(event.error));
        }
      },
    );
  });
}

async function pushImage(docker: Docker, image: string): Promise<void> {
  await followStream(
    docker,
    await docker
      .getImage(image)
      .push({ authconfig: { serveraddress: 'localhost:5000' } }),
  );
}

/**
 * Publish a newer image under the tag the app runs with:
 * the app image with another /app/version, committed from a throwaway container.
 * The local tag is dropped afterwards, so the self-update has to pull it.
 */
async function pushNextImage(docker: Docker, imageId: string): Promise<string> {
  const builder = await docker.createContainer({
    Image: imageId,
    Entrypoint: ['sh', '-c'],
    Cmd: [`echo ${NEXT_VERSION} > /app/version`],
  });
  try {
    await builder.start();
    await builder.wait();
    const committed = await builder.commit({
      repo: 'localhost:5000/tugtainer',
      tag: 'tests',
      changes: ['ENTRYPOINT ["/app/entrypoint.sh"]', 'CMD ["python3"]'],
    });
    await pushImage(docker, APP_IMAGE);
    await docker.getImage(APP_IMAGE).remove();
    return committed.Id as string;
  } finally {
    await builder.remove({ force: true });
  }
}

async function waitForVersion(
  request: APIRequestContext,
  version: string,
): Promise<void> {
  await expect
    .poll(
      async () => {
        try {
          const res = await request.get('/api/public/version');
          return res.ok() ? (await res.json()).image_version : null;
        } catch {
          // The app is unavailable while its container is replaced
          return null;
        }
      },
      { timeout: 180_000, intervals: [2_000] },
    )
    .toBe(version);
}

async function containerExists(docker: Docker, name: string): Promise<boolean> {
  try {
    await docker.getContainer(name).inspect();
    return true;
  } catch {
    return false;
  }
}

test.describe('self-update', () => {
  test.setTimeout(300_000);

  test('replaces the app container with the newer image of its tag', async ({
    authorizedRequest: request,
  }) => {
    const docker = getDocker();
    const before = await docker.getContainer(APP_CONTAINER).inspect();
    expect(before.Config.Image).toBe(APP_IMAGE);

    // Same image in the registry: refused before anything is touched
    await pushImage(docker, APP_IMAGE);
    const noUpdate = await request.post('/api/self_update/start');
    expect(noUpdate.status()).toBe(409);
    expect((await noUpdate.json()).detail).toContain('No newer image');

    const nextImageId = await pushNextImage(docker, before.Image);

    const start = await request.post('/api/self_update/start');
    expect(start.status(), await start.text()).toBe(202);

    await waitForVersion(request, NEXT_VERSION);
    // The new container generates a new JWT secret
    await login(request);
    await expect
      .poll(
        async () => {
          const res = await request.get('/api/self_update/status');
          const status = res.ok() ? (await res.json()).state?.status : null;
          return FINAL_STATUSES.includes(status);
        },
        { timeout: 120_000, intervals: [2_000] },
      )
      .toBe(true);
    const status = await (await request.get('/api/self_update/status')).json();
    expect(status.state.status, status.state.error).toBe('succeeded');

    const after = await docker.getContainer(APP_CONTAINER).inspect();
    expect(after.Id).not.toBe(before.Id);
    expect(after.Image).toBe(nextImageId);
    expect(after.Config.Image).toBe(APP_IMAGE);
    expect(after.Mounts.map((m) => m.Destination)).toContain('/tugtainer');
    expect(await containerExists(docker, `${APP_CONTAINER}-old`)).toBe(false);
    await expect
      .poll(() => containerExists(docker, `${APP_CONTAINER}-self-update`))
      .toBe(false);
  });
});
