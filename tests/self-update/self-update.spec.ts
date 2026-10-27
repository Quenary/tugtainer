import { expect, type APIRequestContext } from '@playwright/test';
import type Docker from 'dockerode';
import { login, test } from '../fixtures/auth-request.fixture';
import { getDocker } from '../shared/util/docker.util';

const APP_CONTAINER = 'tests-tugtainer';
const APP_IMAGE = 'localhost:5000/tugtainer:tests';
const NEXT_VERSION = 'tests-next';
const BROKEN_VERSION = 'tests-broken';
const APP_ENTRYPOINT = '["/app/entrypoint.sh"]';
const BROKEN_ENTRYPOINT = '["sh", "-c", "exit 1"]';
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
async function pushNextImage(
  docker: Docker,
  imageId: string,
  version: string,
  entrypoint = APP_ENTRYPOINT,
): Promise<string> {
  const builder = await docker.createContainer({
    Image: imageId,
    Entrypoint: ['sh', '-c'],
    Cmd: [`echo ${version} > /app/version`],
  });
  try {
    await builder.start();
    await builder.wait();
    const committed = await builder.commit({
      repo: 'localhost:5000/tugtainer',
      tag: 'tests',
      changes: [`ENTRYPOINT ${entrypoint}`, 'CMD ["python3"]'],
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

async function getVersion(request: APIRequestContext): Promise<string> {
  return (await (await request.get('/api/public/version')).json())
    .image_version;
}

/**
 * Sign in again (the restarted app generates a new JWT secret)
 * and wait for the final status of the self-update.
 */
async function waitForResult(
  request: APIRequestContext,
): Promise<{ status: string; error: string | null }> {
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
  return (await (await request.get('/api/self_update/status')).json()).state;
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
  // Both replace the app container
  test.describe.configure({ mode: 'serial' });
  test.setTimeout(420_000);

  test('rolls back to the old container when the new image is broken', async ({
    authorizedRequest: request,
  }) => {
    const docker = getDocker();
    const before = await docker.getContainer(APP_CONTAINER).inspect();
    const oldVersion = await getVersion(request);

    await pushNextImage(
      docker,
      before.Image,
      BROKEN_VERSION,
      BROKEN_ENTRYPOINT,
    );

    const start = await request.post('/api/self_update/start');
    expect(start.status(), await start.text()).toBe(202);

    // The broken container exits and never gets healthy,
    // the helper waits for the self-update health timeout (120s)
    // and starts the old container again
    await expect
      .poll(
        async () => {
          try {
            const app = await docker.getContainer(APP_CONTAINER).inspect();
            if (
              app.Id !== before.Id ||
              app.State.StartedAt === before.State.StartedAt
            ) {
              return false;
            }
            return (await request.get('/api/public/health')).ok();
          } catch {
            return false;
          }
        },
        { timeout: 300_000, intervals: [3_000] },
      )
      .toBe(true);
    const state = await waitForResult(request);
    expect(state.status, state.error ?? '').toBe('rolled_back');
    expect(state.error).toContain('unhealthy');

    const after = await docker.getContainer(APP_CONTAINER).inspect();
    expect(after.Id).toBe(before.Id);
    expect(after.Image).toBe(before.Image);
    expect(after.State.Running).toBe(true);
    expect(await getVersion(request)).toBe(oldVersion);
    expect(await containerExists(docker, `${APP_CONTAINER}-old`)).toBe(false);
    await expect
      .poll(() => containerExists(docker, `${APP_CONTAINER}-self-update`))
      .toBe(false);
  });

  test('replaces the app container with the newer image of its tag', async ({
    authorizedRequest: request,
  }) => {
    const docker = getDocker();
    const before = await docker.getContainer(APP_CONTAINER).inspect();
    expect(before.Config.Image).toBe(APP_IMAGE);

    // Same image in the registry: refused before anything is touched.
    // The tag may point to the broken image pulled by the rollback test.
    await docker
      .getImage(before.Image)
      .tag({ repo: 'localhost:5000/tugtainer', tag: 'tests' });
    await pushImage(docker, APP_IMAGE);
    const noUpdate = await request.post('/api/self_update/start');
    expect(noUpdate.status()).toBe(409);
    expect((await noUpdate.json()).detail).toContain('No newer image');

    const nextImageId = await pushNextImage(docker, before.Image, NEXT_VERSION);

    const start = await request.post('/api/self_update/start');
    expect(start.status(), await start.text()).toBe(202);

    await waitForVersion(request, NEXT_VERSION);
    const state = await waitForResult(request);
    expect(state.status, state.error ?? '').toBe('succeeded');

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
