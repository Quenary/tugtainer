import { test as base } from '@playwright/test';
import type Docker from 'dockerode';
import {
  apiAtLeast,
  connectContainerToNetwork,
  engineApiVersion,
  getDocker,
  pullImage,
  removeContainerIfExists,
  removeImageTagIfExists,
  removeNetworkIfExists,
  removeVolumeIfExists,
} from '../shared/util/docker.util';

/** Distinct from check-container's 3.22/3.23 pair so the tests can run in parallel. */
export const SOURCE_IMAGE = 'alpine:3.20';
export const STALE_TAG = 'alpine:3.21';

export const APP_NAME = 'tugtainer-test-update-app';
export const DB_NAME = 'tugtainer-test-update-db';
export const PRIMARY_NET = 'tugtainer-test-update-primary';
export const EXTRA_NET = 'tugtainer-test-update-extra';
export const EXTRA_ALIAS = 'app';
export const PRIMARY_ALIAS = 'primary-app';
export const LINK_ALIAS = 'db';
export const BIND_VOLUME = 'tugtainer-test-update-bind';
export const MOUNT_VOLUME = 'tugtainer-test-update-mount';
export const DATA_VOLUME = 'tugtainer-test-update-data';
export const USER_LABEL = 'com.example.keep';
export const PUBLISHED_PORT = '18991';

const TEST_LABEL = 'update-extra-network';
const PRIMARY_SUBNET = '172.31.210.0/24';
const EXTRA_SUBNET = '172.31.211.0/24';
const PRIMARY_IP = '172.31.210.20';
const EXTRA_IP = '172.31.211.20';
const PRIMARY_MAC = '02:42:ac:1f:d2:14';
const ALPINE_PATH =
  'PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin';

export interface OutdatedAlpineExtraNetwork {
  name: string;
  image: string;
  extraNetwork: string;
  primaryNetwork: string;
  extraAlias: string;
  primaryAlias: string;
  linkTargetName: string;
  linkAlias: string;
  userLabel: string;
  publishedPort: string;
  dataPath: string;
  anonPath: string;
  gatewayPriority: number | null;
}

async function cleanup(): Promise<void> {
  const docker = getDocker();
  await removeContainerIfExists(docker, APP_NAME, { removeVolumes: true });
  await removeContainerIfExists(docker, DB_NAME);
  await removeVolumeIfExists(docker, BIND_VOLUME);
  await removeVolumeIfExists(docker, MOUNT_VOLUME);
  await removeVolumeIfExists(docker, DATA_VOLUME);
  await removeNetworkIfExists(docker, EXTRA_NET);
  await removeNetworkIfExists(docker, PRIMARY_NET);
  await removeImageTagIfExists(docker, STALE_TAG);
}

async function mkdirVolumeSubpath(docker: Docker): Promise<void> {
  const prep = await docker.createContainer({
    Image: SOURCE_IMAGE,
    Cmd: ['mkdir', '-p', '/v/kept'],
    HostConfig: {
      Mounts: [{ Type: 'volume', Source: MOUNT_VOLUME, Target: '/v' }],
    },
  });
  try {
    await prep.start();
    const status = await prep.wait();
    if (status.StatusCode !== 0) {
      throw new Error(`failed to create volume subpath: ${status.StatusCode}`);
    }
  } finally {
    await prep.remove({ force: true });
  }
}

function labeledNetwork(
  name: string,
  subnet: string,
): Docker.NetworkCreateOptions {
  return {
    Name: name,
    CheckDuplicate: true,
    Labels: { 'dev.quenary.tugtainer.test': TEST_LABEL },
    IPAM: {
      Driver: 'default',
      Config: [{ Subnet: subnet, Gateway: subnet.replace('.0/24', '.1') }],
    },
  };
}

/**
 * Outdated alpine container on a primary user-defined network, plus a second
 * network connected with alias, link, and a static address. Host and container
 * config cover the fields recreate must send back to the engine.
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

      await docker.createVolume({
        Name: BIND_VOLUME,
        Labels: { 'dev.quenary.tugtainer.test': TEST_LABEL },
      });
      await docker.createVolume({
        Name: MOUNT_VOLUME,
        Labels: { 'dev.quenary.tugtainer.test': TEST_LABEL },
      });
      await docker.createVolume({
        Name: DATA_VOLUME,
        Labels: { 'dev.quenary.tugtainer.test': TEST_LABEL },
      });
      const api = await engineApiVersion(docker);
      const volumeSubpath = apiAtLeast(api, 1, 45);
      const tmpfsOptions = apiAtLeast(api, 1, 46);
      const gatewayPriority = apiAtLeast(api, 1, 48) ? 10 : null;
      if (volumeSubpath) {
        await mkdirVolumeSubpath(docker);
      }
      await docker.createNetwork(labeledNetwork(EXTRA_NET, EXTRA_SUBNET));
      await docker.createNetwork(labeledNetwork(PRIMARY_NET, PRIMARY_SUBNET));

      const db = await docker.createContainer({
        Image: SOURCE_IMAGE,
        name: DB_NAME,
        Cmd: ['sleep', 'infinity'],
        Labels: { 'dev.quenary.tugtainer.test': TEST_LABEL },
        HostConfig: { NetworkMode: EXTRA_NET },
        NetworkingConfig: {
          EndpointsConfig: {
            [EXTRA_NET]: {
              IPAMConfig: { IPv4Address: '172.31.211.10' },
            },
          },
        },
      });
      await db.start();

      const app = await docker.createContainer({
        Image: STALE_TAG,
        name: APP_NAME,
        Hostname: 'tugtest',
        Domainname: 'example',
        User: 'nobody',
        WorkingDir: '/tmp',
        Entrypoint: ['/bin/sleep'],
        Cmd: ['infinity'],
        Env: [ALPINE_PATH, 'CUSTOM=preserved'],
        Labels: {
          'dev.quenary.tugtainer.test': TEST_LABEL,
          [USER_LABEL]: 'yes',
        },
        StopSignal: 'SIGUSR1',
        StopTimeout: 15,
        Tty: true,
        ExposedPorts: { '8080/tcp': {} },
        Healthcheck: {
          Test: ['CMD', 'true'],
          Interval: 1_000_000_000,
          Timeout: 1_000_000_000,
          Retries: 3,
          StartPeriod: 1_000_000_000,
          StartInterval: 1_000_000_000,
        },
        HostConfig: {
          NetworkMode: PRIMARY_NET,
          ExtraHosts: [
            'host.docker.internal:host-gateway',
            'test.local:127.0.0.1',
          ],
          PortBindings: {
            '8080/tcp': [{ HostIp: '127.0.0.1', HostPort: PUBLISHED_PORT }],
          },
          PublishAllPorts: false,
          RestartPolicy: { Name: 'on-failure', MaximumRetryCount: 2 },
          LogConfig: {
            Type: 'json-file',
            Config: { 'max-size': '1m', 'max-file': '2' },
          },
          CapAdd: ['NET_ADMIN'],
          CapDrop: ['MKNOD'],
          SecurityOpt: ['no-new-privileges:true'],
          ReadonlyRootfs: true,
          Tmpfs: { '/tmp': 'rw,noexec,nosuid,size=16m' },
          Sysctls: { 'net.ipv4.ip_unprivileged_port_start': '1024' },
          Ulimits: [{ Name: 'nofile', Soft: 1024, Hard: 2048 }],
          Init: true,
          ShmSize: 64 * 1024 * 1024,
          Memory: 64 * 1024 * 1024,
          MemorySwap: 128 * 1024 * 1024,
          MemoryReservation: 32 * 1024 * 1024,
          NanoCpus: 500_000_000,
          CpuShares: 512,
          PidsLimit: 128,
          BlkioWeight: 300,
          Dns: ['1.1.1.1'],
          DnsSearch: ['example'],
          GroupAdd: ['65534'],
          OomScoreAdj: 100,
          IpcMode: 'private',
          // -v binds stay in HostConfig.Binds, including the SELinux flag.
          // --mount ones stay in HostConfig.Mounts with their options.
          Binds: [`${DATA_VOLUME}:/data`, `${BIND_VOLUME}:/bind:ro,z`],
          Mounts: [
            {
              Type: 'bind',
              Source: '/tmp',
              Target: '/mnt/bind',
              ReadOnly: true,
              BindOptions: {
                Propagation: 'rprivate',
                NonRecursive: true,
                CreateMountpoint: true,
                ReadOnlyNonRecursive: true,
              },
            },
            {
              Type: 'volume',
              Source: MOUNT_VOLUME,
              Target: '/mount',
              VolumeOptions: {
                NoCopy: true,
                Labels: { 'dev.quenary.tugtainer.test': TEST_LABEL },
                ...(volumeSubpath ? { Subpath: 'kept' } : {}),
              },
            },
            { Type: 'volume', Target: '/anon' },
            {
              Type: 'tmpfs',
              Target: '/mnt/tmpfs',
              TmpfsOptions: {
                SizeBytes: 16 * 1024 * 1024,
                Mode: 0o755,
                // API 1.48 stores this as a list of string lists.
                ...(tmpfsOptions ? { Options: [['noexec']] } : {}),
              },
            },
          ] as unknown as Docker.MountConfig,
        },
        NetworkingConfig: {
          EndpointsConfig: {
            [PRIMARY_NET]: {
              IPAMConfig: { IPv4Address: PRIMARY_IP },
              Aliases: [PRIMARY_ALIAS],
              MacAddress: PRIMARY_MAC,
              ...(gatewayPriority != null
                ? { GwPriority: gatewayPriority }
                : {}),
            } as Docker.EndpointSettings,
          },
        },
      });
      await app.start();
      await connectContainerToNetwork(docker, EXTRA_NET, APP_NAME, {
        aliases: [EXTRA_ALIAS],
        links: [`${DB_NAME}:${LINK_ALIAS}`],
        ipv4Address: EXTRA_IP,
      });

      await use({
        name: APP_NAME,
        image: STALE_TAG,
        extraNetwork: EXTRA_NET,
        primaryNetwork: PRIMARY_NET,
        extraAlias: EXTRA_ALIAS,
        primaryAlias: PRIMARY_ALIAS,
        linkTargetName: DB_NAME,
        linkAlias: LINK_ALIAS,
        userLabel: USER_LABEL,
        publishedPort: PUBLISHED_PORT,
        dataPath: '/data/marker',
        anonPath: '/anon/marker',
        gatewayPriority,
      });
    } finally {
      await cleanup();
    }
  },
});
