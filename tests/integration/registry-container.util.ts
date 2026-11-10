import type Docker from 'dockerode';
import {
  getDocker,
  removeContainerIfExists,
  removeImageTagIfExists,
  removeVolumeIfExists,
} from '../shared/util/docker.util';
import { imageName, publishFrom } from '../shared/util/registry.util';

export interface RegistryContainer {
  docker: Docker;
  name: string;
  image: string;
  digest: string;
  volume: string | null;
  cleanup: () => Promise<void>;
}

/**
 * Publish alpine to the local registry and start a container from that tag.
 * The tag stays local so the container can be created; callers that need a
 * pull replace it afterwards.
 */
export async function startRegistryContainer(options: {
  suffix: string;
  source?: string;
  start?: boolean;
  /** When false, only the tag is published. */
  create?: boolean;
  /** Use an image that is already present. Does not push another tag. */
  publish?: boolean;
  labels?: Record<string, string>;
  imageRef?: string;
  cidfile?: string;
  volume?: boolean;
}): Promise<RegistryContainer> {
  const docker = getDocker();
  const image = imageName(`tugtainer-test/${options.suffix}`, 'app');
  const name = `tugtainer-test-${options.suffix}`;
  const volume = options.volume ? `${name}-data` : null;
  const digest =
    options.publish === false
      ? (options.imageRef ?? '')
      : await publishFrom(docker, options.source ?? 'alpine:3.20', image);
  if (options.create !== false) {
    if (volume) {
      await docker.createVolume({ Name: volume });
    }
    const container = await docker.createContainer({
      Image: options.imageRef ?? image,
      name,
      Cmd: ['sleep', 'infinity'],
      Labels: {
        'dev.quenary.tugtainer.test': 'registry',
        ...options.labels,
      },
      HostConfig: {
        Binds: volume ? [`${volume}:/data`] : undefined,
        ContainerIDFile: options.cidfile,
      },
    });
    if (options.start !== false) {
      await container.start();
    }
  }

  return {
    docker,
    name,
    image,
    digest,
    volume,
    cleanup: async () => {
      if (options.create !== false) {
        await removeContainerIfExists(docker, name, { removeVolumes: true });
      }
      if (volume) {
        await removeVolumeIfExists(docker, volume);
      }
      if (options.publish !== false) {
        await removeImageTagIfExists(docker, image);
      }
    },
  };
}
