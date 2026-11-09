import type Docker from 'dockerode';

/**
 * Stable container settings that an update must recreate.
 * Image identity, runtime state, image labels, and addresses Docker assigns
 * (gateway, endpoint id, generated aliases) are left out.
 */
export function pickPreservedConfig(
  inspect: Docker.ContainerInspectInfo,
): PreservedConfig {
  const config = inspect.Config as Docker.ContainerInspectInfo['Config'] & {
    StopSignal?: string;
    StopTimeout?: number;
  };
  const host = inspect.HostConfig;
  return {
    name: inspect.Name,
    image: config?.Image ?? null,
    user: config?.User ?? '',
    workingDir: config?.WorkingDir ?? '',
    hostname: stableHostname(inspect.Id, config?.Hostname),
    domainname: config?.Domainname ?? '',
    entrypoint: config?.Entrypoint ?? null,
    cmd: config?.Cmd ?? null,
    stopSignal: config?.StopSignal ?? null,
    stopTimeout: config?.StopTimeout ?? null,
    tty: Boolean(config?.Tty),
    env: userEnv(config?.Env),
    exposedPorts: sorted(Object.keys(config?.ExposedPorts ?? {})),
    healthcheck: healthcheck(config?.Healthcheck),
    binds: sorted(host?.Binds),
    mounts: mounts(inspect.Mounts),
    portBindings: portBindings(host?.PortBindings),
    publishAllPorts: Boolean(host?.PublishAllPorts),
    restart: host?.RestartPolicy
      ? {
          name: host.RestartPolicy.Name,
          maximumRetryCount: host.RestartPolicy.MaximumRetryCount ?? 0,
        }
      : null,
    log: host?.LogConfig
      ? {
          type: host.LogConfig.Type,
          config: sortedEntries(
            host.LogConfig.Config as Record<string, string>,
          ),
        }
      : null,
    capAdd: sorted(asStrings(host?.CapAdd)),
    capDrop: sorted(asStrings(host?.CapDrop)),
    securityOpt: sorted(asStrings(host?.SecurityOpt)),
    readonlyRootfs: Boolean(host?.ReadonlyRootfs),
    tmpfs: sortedEntries(host?.Tmpfs),
    sysctls: sortedEntries(host?.Sysctls),
    ulimits: ulimits(host?.Ulimits),
    init: host?.Init ?? null,
    shmSize: host?.ShmSize ?? null,
    memory: host?.Memory ?? 0,
    memorySwap: host?.MemorySwap ?? 0,
    memoryReservation: host?.MemoryReservation ?? 0,
    nanoCpus: host?.NanoCpus ?? 0,
    cpuShares: host?.CpuShares ?? 0,
    pidsLimit: host?.PidsLimit ?? null,
    blkioWeight: host?.BlkioWeight ?? 0,
    dns: sorted(asStrings(host?.Dns)),
    dnsSearch: sorted(host?.DnsSearch),
    extraHosts: sorted(asStrings(host?.ExtraHosts)),
    groupAdd: sorted(host?.GroupAdd),
    oomScoreAdj: host?.OomScoreAdj ?? 0,
    ipcMode: host?.IpcMode ?? '',
    networks: networks(inspect),
  };
}

interface PreservedConfig {
  name: string;
  image: string | null;
  user: string;
  workingDir: string;
  hostname: string;
  domainname: string;
  entrypoint: string | string[] | null;
  cmd: string[] | null;
  stopSignal: string | null;
  stopTimeout: number | null;
  tty: boolean;
  env: string[];
  exposedPorts: string[];
  healthcheck: {
    test: string[];
    interval: number;
    timeout: number;
    retries: number;
    startPeriod: number;
    startInterval: number;
  } | null;
  binds: string[];
  mounts: {
    type: string;
    name: string | null;
    source: string | null;
    destination: string;
    rw: boolean;
  }[];
  portBindings: string[];
  publishAllPorts: boolean;
  restart: { name: string; maximumRetryCount: number } | null;
  log: { type: string; config: string[] } | null;
  capAdd: string[];
  capDrop: string[];
  securityOpt: string[];
  readonlyRootfs: boolean;
  tmpfs: string[];
  sysctls: string[];
  ulimits: string[];
  init: boolean | null;
  shmSize: number | null;
  memory: number;
  memorySwap: number;
  memoryReservation: number;
  nanoCpus: number;
  cpuShares: number;
  pidsLimit: number | null;
  blkioWeight: number;
  dns: string[];
  dnsSearch: string[];
  extraHosts: string[];
  groupAdd: string[];
  oomScoreAdj: number;
  ipcMode: string;
  networks: Record<
    string,
    {
      ipv4: string | null;
      mac: string | null;
      gwPriority: number | null;
      aliases: string[];
      links: string[];
    }
  >;
}

function stableHostname(id: string, hostname: string | undefined): string {
  // Docker fills an empty hostname with the container id. Recreate drops it.
  if (!hostname || id.includes(hostname)) {
    return '';
  }
  return hostname;
}

function sorted(values: readonly string[] | null | undefined): string[] {
  return [...(values ?? [])].sort();
}

function asStrings(values: unknown): string[] {
  if (!Array.isArray(values)) {
    return [];
  }
  return values.map((item) => String(item));
}

function sortedEntries(
  values: Record<string, string> | null | undefined,
): string[] {
  return Object.entries(values ?? {})
    .map(([key, value]) => `${key}=${value}`)
    .sort();
}

function userEnv(env: string[] | null | undefined): string[] {
  return sorted((env ?? []).filter((item) => !item.startsWith('PATH=')));
}

function healthcheck(
  value:
    Docker.ContainerInspectInfo['Config']['Healthcheck'] | null | undefined,
): PreservedConfig['healthcheck'] {
  if (!value?.Test?.length) {
    return null;
  }
  return {
    test: value.Test,
    interval: value.Interval ?? 0,
    timeout: value.Timeout ?? 0,
    retries: value.Retries ?? 0,
    startPeriod: value.StartPeriod ?? 0,
    startInterval: value.StartInterval ?? 0,
  };
}

function ulimits(
  values: Docker.HostConfig['Ulimits'] | null | undefined,
): string[] {
  return sorted(
    (values ?? []).map((item) => `${item.Name}=${item.Soft}:${item.Hard}`),
  );
}

function portBindings(value: Docker.HostConfig['PortBindings']): string[] {
  const bindings = (value ?? {}) as Record<
    string,
    { HostIp?: string; HostPort?: string }[] | null
  >;
  const rows: string[] = [];
  for (const [port, entries] of Object.entries(bindings)) {
    for (const entry of entries ?? []) {
      rows.push(`${entry.HostIp ?? ''}:${entry.HostPort ?? ''}->${port}`);
    }
  }
  return rows.sort();
}

function mounts(
  values: Docker.ContainerInspectInfo['Mounts'] | undefined,
): PreservedConfig['mounts'] {
  return (values ?? [])
    .map((mount) => ({
      type: mount.Type,
      name: mount.Name || null,
      source: mount.Source || null,
      destination: mount.Destination,
      rw: mount.RW !== false,
    }))
    .sort((left, right) => left.destination.localeCompare(right.destination));
}

export interface HostMountSpec {
  type: string;
  target: string;
  source: string | null;
  readOnly: boolean;
  bindOptions: string | null;
  volumeOptions: string | null;
  tmpfsOptions: string | null;
}

interface EngineMount {
  Type?: string;
  Target?: string;
  Source?: string;
  ReadOnly?: boolean;
  BindOptions?: Record<string, unknown> | null;
  VolumeOptions?: Record<string, unknown> | null;
  TmpfsOptions?: Record<string, unknown> | null;
}

/** Long-syntax mounts from HostConfig, including options recreate must copy. */
export function pickHostMounts(
  inspect: Docker.ContainerInspectInfo,
): HostMountSpec[] {
  const mounts = (inspect.HostConfig?.Mounts ?? []) as EngineMount[];
  return mounts
    .map((mount) => ({
      type: mount.Type ?? '',
      target: mount.Target ?? '',
      source: mount.Source || null,
      readOnly: mount.ReadOnly === true,
      bindOptions: stableOptions(mount.BindOptions),
      volumeOptions: stableOptions(mount.VolumeOptions),
      tmpfsOptions: stableOptions(mount.TmpfsOptions),
    }))
    .sort((left, right) => left.target.localeCompare(right.target));
}

/**
 * Anonymous volumes have no source until recreate fills the name from the
 * runtime mount. Compare the options either way.
 */
export function preservedHostMounts(
  after: Docker.ContainerInspectInfo,
  before: Docker.ContainerInspectInfo,
): HostMountSpec[] {
  const prior = new Map(
    pickHostMounts(before).map((mount) => [mount.target, mount]),
  );
  return pickHostMounts(after).map((mount) => {
    const previous = prior.get(mount.target);
    if (previous && !previous.source) {
      return { ...mount, source: null };
    }
    return mount;
  });
}

function stableOptions(
  value: Record<string, unknown> | null | undefined,
): string | null {
  if (!value || Object.keys(value).length === 0) {
    return null;
  }
  return JSON.stringify(sortJson(value));
}

function sortJson(value: unknown): unknown {
  if (Array.isArray(value)) {
    return value.map((item) => sortJson(item));
  }
  if (value && typeof value === 'object') {
    return Object.fromEntries(
      Object.entries(value as Record<string, unknown>)
        .sort(([left], [right]) => left.localeCompare(right))
        .map(([key, item]) => [key, sortJson(item)]),
    );
  }
  return value ?? null;
}

function networks(
  inspect: Docker.ContainerInspectInfo,
): PreservedConfig['networks'] {
  const attached = inspect.NetworkSettings?.Networks ?? {};
  const primary = inspect.HostConfig?.NetworkMode ?? '';
  const result: PreservedConfig['networks'] = {};
  for (const name of Object.keys(attached).sort()) {
    const endpoint = attached[name];
    if (!endpoint) {
      continue;
    }
    const ipv4 = endpoint.IPAMConfig?.IPv4Address ?? null;
    result[name] = {
      ipv4,
      // A MAC is stable only for the primary network when an address was
      // requested. Docker assigns a new one on the default bridge and when
      // a secondary network is reconnected.
      mac:
        name === primary && ipv4 && endpoint.MacAddress
          ? endpoint.MacAddress.toLowerCase()
          : null,
      gwPriority:
        (endpoint as { GwPriority?: number | null }).GwPriority ?? null,
      aliases: sorted(
        (endpoint.Aliases ?? []).filter(
          (alias: string) => !/^[0-9a-f]{12}$/.test(alias),
        ),
      ),
      links: sorted(endpoint.Links ?? []),
    };
  }
  return result;
}
