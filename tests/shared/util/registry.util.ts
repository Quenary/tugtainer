import type Docker from 'dockerode';
import { pullImage, removeImageTagIfExists } from './docker.util';

const REGISTRY = 'localhost:5000';

export interface RegistryCredentials {
  username: string;
  password: string;
  serveraddress: string;
}

export function imageName(
  repo: string,
  tag: string,
  registry = REGISTRY,
): string {
  return `${registry}/${repo}:${tag}`;
}

export async function publishFrom(
  docker: Docker,
  source: string,
  target: string,
  auth?: RegistryCredentials,
): Promise<string> {
  await pullImage(docker, source);
  const { repo, tag } = splitTag(target);
  await docker.getImage(source).tag({ repo, tag });
  await pushTag(docker, target, auth);
  return digestOf(docker, target);
}

/**
 * Commit a new layer before publishing.
 *
 * A shared image id collects a RepoDigest for every tag pushed from it.
 * Check asks the registry once per digest, so a private registry the app
 * cannot read would repeat that failure for every accumulated tag.
 */
export async function publishCommitted(
  docker: Docker,
  source: string,
  target: string,
  auth?: RegistryCredentials,
): Promise<string> {
  await pullImage(docker, source);
  const builder = await docker.createContainer({
    Image: source,
    Cmd: ['/bin/true'],
  });
  try {
    await builder.start();
    await builder.wait();
    const { repo, tag } = splitTag(target);
    // A repeated commit of the same source and label reuses the image id,
    // and that id then collects a RepoDigest for every registry it is pushed
    // to. Check walks those digests, so the marker has to be unique.
    const marker = `${source.replace(/:/g, '-')}-${Date.now().toString(36)}-${Math.random().toString(16).slice(2)}`;
    await builder.commit({
      repo,
      tag,
      changes: [`LABEL dev.quenary.tugtainer.test.commit=${marker}`],
    });
  } finally {
    await builder.remove({ force: true });
  }
  await pushTag(docker, target, auth);
  return digestOf(docker, target);
}

/** Push a different image under an existing tag, then drop the local tag. */
export async function replacePublishedTag(
  docker: Docker,
  source: string,
  target: string,
  auth?: RegistryCredentials,
): Promise<void> {
  await publishFrom(docker, source, target, auth);
  await removeImageTagIfExists(docker, target);
}

/** Publish a committed image whose healthcheck is the given Dockerfile instruction. */
export async function publishImageHealthcheck(
  docker: Docker,
  source: string,
  target: string,
  healthcheck: string,
  options?: { dropLocal?: boolean },
): Promise<void> {
  await pullImage(docker, source);
  const builder = await docker.createContainer({
    Image: source,
    Cmd: ['/bin/true'],
  });
  try {
    await builder.start();
    await builder.wait();
    const { repo, tag } = splitTag(target);
    await builder.commit({
      repo,
      tag,
      changes: ['CMD ["/bin/sleep", "infinity"]', healthcheck],
    });
  } finally {
    await builder.remove({ force: true });
  }
  await pushTag(docker, target);
  if (options?.dropLocal) {
    await removeImageTagIfExists(docker, target);
  }
}

export async function publishFailingHealthcheck(
  docker: Docker,
  source: string,
  target: string,
): Promise<void> {
  await pullImage(docker, source);
  const builder = await docker.createContainer({
    Image: source,
    Cmd: ['/bin/true'],
  });
  try {
    await builder.start();
    await builder.wait();
    const { repo, tag } = splitTag(target);
    await builder.commit({
      repo,
      tag,
      changes: [
        'CMD ["/bin/sleep", "infinity"]',
        'HEALTHCHECK --interval=1s --timeout=1s --start-period=0s --retries=1 CMD exit 1',
      ],
    });
  } finally {
    await builder.remove({ force: true });
  }
  await pushTag(docker, target);
  await removeImageTagIfExists(docker, target);
}

async function pushTag(
  docker: Docker,
  image: string,
  auth?: RegistryCredentials,
): Promise<void> {
  const stream = await docker.getImage(image).push({
    authconfig: auth ?? { serveraddress: registryHost(image) },
  });
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

async function digestOf(docker: Docker, target: string): Promise<string> {
  const { repo } = splitTag(target);
  const info = await docker.getImage(target).inspect();
  const digest = (info.RepoDigests ?? []).find((item) =>
    item.startsWith(`${repo}@`),
  );
  if (!digest) {
    throw new Error(`Registry did not return a digest for ${target}`);
  }
  return digest;
}

function registryHost(image: string): string {
  const slash = image.indexOf('/');
  return slash === -1 ? REGISTRY : image.slice(0, slash);
}

function splitTag(image: string): { repo: string; tag: string } {
  const slash = image.lastIndexOf('/');
  const colon = image.lastIndexOf(':');
  if (colon > slash) {
    return { repo: image.slice(0, colon), tag: image.slice(colon + 1) };
  }
  return { repo: image, tag: 'latest' };
}
