import type Docker from 'dockerode';
import {
  execInContainer,
  getDocker,
  removeContainerIfExists,
  removeImageTagIfExists,
  removeVolumeIfExists,
} from '../shared/util/docker.util';
import {
  imageName,
  publishCommitted,
  type RegistryCredentials,
} from '../shared/util/registry.util';

/** Test-only credentials. The private registry htpasswd uses the same pair. */
export const PRIVATE_REGISTRY_AUTH: RegistryCredentials = {
  username: 'tugtest',
  password: 'tugtest-secret',
  serveraddress: 'localhost:5001',
};

export const UNAUTHORIZED_REGISTRY_AUTH: RegistryCredentials = {
  username: 'tugtest',
  password: 'tugtest-secret',
  serveraddress: 'localhost:5002',
};

export interface PrivateRegistryContainer {
  docker: Docker;
  name: string;
  image: string;
  cleanup: () => Promise<void>;
}

/**
 * Publish an old image to a registry that requires credentials, and run it.
 * Callers push a newer image under the same tag when the test should see
 * an update.
 */
export async function startPrivateRegistryContainer(options: {
  suffix: string;
  registry: string;
  auth: RegistryCredentials;
}): Promise<PrivateRegistryContainer> {
  const docker = getDocker();
  const image = imageName(
    `tugtainer-test/${options.suffix}`,
    'app',
    options.registry,
  );
  const name = `tugtainer-test-${options.suffix}`;
  const volume = `${name}-data`;
  await removeContainerIfExists(docker, name, { removeVolumes: true });
  await removeVolumeIfExists(docker, volume);
  await publishCommitted(docker, 'alpine:3.20', image, options.auth);
  await docker.createVolume({ Name: volume });
  const container = await docker.createContainer({
    Image: image,
    name,
    Cmd: ['sleep', 'infinity'],
    Labels: { 'dev.quenary.tugtainer.test': 'private-registry' },
    HostConfig: { Binds: [`${volume}:/data`] },
  });
  await container.start();
  await execInContainer(docker, name, [
    'sh',
    '-c',
    'echo preserved > /data/marker',
  ]);

  return {
    docker,
    name,
    image,
    cleanup: async () => {
      await removeContainerIfExists(docker, name, { removeVolumes: true });
      await removeVolumeIfExists(docker, volume);
      await removeImageTagIfExists(docker, image);
    },
  };
}

export async function publishNewerImage(
  docker: Docker,
  image: string,
  auth: RegistryCredentials,
): Promise<void> {
  await publishCommitted(docker, 'alpine:3.21', image, auth);
  await removeImageTagIfExists(docker, image);
}

/** The check cannot mark a registry it cannot read, so the pull has to be forced. */
export async function markUpdateAvailable(name: string): Promise<void> {
  const docker = getDocker();
  const output = await execInContainer(docker, 'tests-tugtainer', [
    'python',
    '-c',
    [
      'import sqlite3, sys',
      'name = sys.argv[1]',
      'con = sqlite3.connect("/tugtainer/tugtainer.db")',
      'cur = con.execute("UPDATE containers SET update_available=1 WHERE name=?", (name,))',
      'con.commit()',
      'print(cur.rowcount)',
    ].join('\n'),
    name,
  ]);
  if (!output.includes('1')) {
    throw new Error(`Container row was not marked available: ${output}`);
  }
}
