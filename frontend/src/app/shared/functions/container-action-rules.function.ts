import {
  EContainerStatus,
  TControlContainerCommand,
} from '../../features/containers/containers.interface';

export interface IContainerActionTarget {
  status: EContainerStatus | string;
  protected?: boolean;
}

export const CONTAINER_ACTION_RULES: Record<
  TControlContainerCommand,
  (status: EContainerStatus | string) => boolean
> = {
  start: (status) => ['created', 'exited'].includes(status),
  stop: (status) => !['created', 'exited', 'dead', 'removing'].includes(status),
  restart: (status) => !['created', 'removing'].includes(status),
  kill: (status) => !['created', 'exited', 'dead', 'removing'].includes(status),
  pause: (status) => status === 'running',
  unpause: (status) => status === 'paused',
};

export function canExecuteContainerCommand(
  container: IContainerActionTarget | null | undefined,
  command: TControlContainerCommand,
): boolean {
  if (!container || container.protected) {
    return false;
  }
  const rule = CONTAINER_ACTION_RULES[command];
  return rule ? rule(container.status) : false;
}

export function filterContainersForCommand<T extends IContainerActionTarget>(
  containers: T[] | null | undefined,
  command: TControlContainerCommand,
): T[] {
  if (!containers || !containers.length) {
    return [];
  }
  return containers.filter((c) => canExecuteContainerCommand(c, command));
}
