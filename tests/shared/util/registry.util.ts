import type Docker from 'dockerode';
import { pullImage, removeImageTagIfExists } from './docker.util';

const REGISTRY = 'localhost:5000';

export function imageName(repo: string, tag: string): string {
  return `${REGISTRY}/${repo}:${tag}`;
}

export async function publishFrom(
  docker: Docker,
  source: string,
  target: string,
): Promise<string> {
  await pullImage(docker, source);
  const { repo, tag } = splitTag(target);
  await docker.getImage(source).tag({ repo, tag });
  await pushTag(docker, target);
  const info = await docker.getImage(target).inspect();
  const digest = (info.RepoDigests ?? []).find((item) =>
    item.startsWith(`${repo}@`),
  );
  if (!digest) {
    throw new Error(`Registry did not return a digest for ${target}`);
  }
  return digest;
}

/** Push a different image under an existing tag, then drop the local tag. */
export async function replacePublishedTag(
  docker: Docker,
  source: string,
  target: string,
): Promise<void> {
  await publishFrom(docker, source, target);
  await removeImageTagIfExists(docker, target);
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

async function pushTag(docker: Docker, image: string): Promise<void> {
  const stream = await docker.getImage(image).push({
    authconfig: { serveraddress: REGISTRY },
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

function splitTag(image: string): { repo: string; tag: string } {
  const slash = image.lastIndexOf('/');
  const colon = image.lastIndexOf(':');
  if (colon > slash) {
    return { repo: image.slice(0, colon), tag: image.slice(colon + 1) };
  }
  return { repo: image, tag: 'latest' };
}
