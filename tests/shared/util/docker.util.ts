import Docker from 'dockerode';

const SOCKET_PATH = process.env.DOCKER_SOCKET ?? '/var/run/docker.sock';

export function getDocker(): Docker {
  return new Docker({ socketPath: SOCKET_PATH });
}

export async function engineApiVersion(
  docker: Docker,
): Promise<[number, number]> {
  const version = await docker.version();
  const [major, minor] = version.ApiVersion.split('.').map((part) =>
    Number(part),
  );
  return [major || 0, minor || 0];
}

export function apiAtLeast(
  api: [number, number],
  major: number,
  minor: number,
): boolean {
  return api[0] > major || (api[0] === major && api[1] >= minor);
}

export async function pullImage(docker: Docker, image: string): Promise<void> {
  try {
    await new Promise<void>((resolve, reject) => {
      docker.pull(image, {}, (err, stream) => {
        if (err) {
          reject(err);
          return;
        }
        if (!stream) {
          reject(new Error(`Pull returned empty stream for ${image}`));
          return;
        }
        docker.modem.followProgress(stream, (followErr) => {
          if (followErr) {
            reject(followErr);
            return;
          }
          resolve();
        });
      });
    });
  } catch (err) {
    // Parallel pulls of the same public tag often fail on a registry handshake
    // while the image is already local. Keep that image; a missing one still fails.
    try {
      await docker.getImage(image).inspect();
    } catch {
      throw err;
    }
  }
}

export async function removeContainerIfExists(
  docker: Docker,
  name: string,
  options?: { removeVolumes?: boolean },
): Promise<void> {
  try {
    const container = docker.getContainer(name);
    await container.inspect();
    try {
      await container.stop({ t: 5 });
    } catch {
      // already stopped
    }
    await container.remove({ force: true, v: options?.removeVolumes ?? false });
  } catch (err) {
    const statusCode = (err as { statusCode?: number }).statusCode;
    if (statusCode !== 404) {
      throw err;
    }
  }
}

export async function removeImageTagIfExists(
  docker: Docker,
  image: string,
): Promise<void> {
  try {
    await docker.getImage(image).remove();
  } catch (err) {
    const statusCode = (err as { statusCode?: number }).statusCode;
    if (statusCode !== 404 && statusCode !== 409) {
      throw err;
    }
  }
}

export async function removeNetworkIfExists(
  docker: Docker,
  name: string,
): Promise<void> {
  try {
    const network = docker.getNetwork(name);
    await network.inspect();
    await network.remove();
  } catch (err) {
    const statusCode = (err as { statusCode?: number }).statusCode;
    if (statusCode !== 404) {
      throw err;
    }
  }
}

export async function removeVolumeIfExists(
  docker: Docker,
  name: string,
): Promise<void> {
  try {
    await docker.getVolume(name).remove();
  } catch (err) {
    const statusCode = (err as { statusCode?: number }).statusCode;
    if (statusCode !== 404) {
      throw err;
    }
  }
}

export async function connectContainerToNetwork(
  docker: Docker,
  networkName: string,
  containerName: string,
  options?: { aliases?: string[]; links?: string[]; ipv4Address?: string },
): Promise<void> {
  await docker.getNetwork(networkName).connect({
    Container: containerName,
    EndpointConfig: {
      Aliases: options?.aliases,
      Links: options?.links,
      IPAMConfig: options?.ipv4Address
        ? { IPv4Address: options.ipv4Address }
        : undefined,
    },
  });
}

export async function execInContainer(
  docker: Docker,
  name: string,
  cmd: string[],
): Promise<string> {
  const exec = await docker.getContainer(name).exec({
    Cmd: cmd,
    AttachStdout: true,
    AttachStderr: true,
    User: 'root',
  });
  const stream = await exec.start({ hijack: true, stdin: false });
  const chunks: Buffer[] = [];
  await new Promise<void>((resolve, reject) => {
    stream.on('data', (chunk: Buffer) => {
      chunks.push(Buffer.from(chunk));
    });
    stream.on('end', () => resolve());
    stream.on('error', reject);
  });
  return Buffer.concat(chunks).toString('utf8');
}
