import { EContainerStatus } from '../../features/containers/containers.interface';
import {
  canExecuteContainerCommand,
  filterContainersForCommand,
  IContainerActionTarget,
} from './container-action-rules.function';

describe('containerActionRules', () => {
  describe('canExecuteContainerCommand', () => {
    it('should return false for null or undefined container', () => {
      expect(canExecuteContainerCommand(null, 'start')).toBe(false);
      expect(canExecuteContainerCommand(undefined, 'stop')).toBe(false);
    });

    it('should return false for protected containers regardless of status or command', () => {
      const protectedRunning: IContainerActionTarget = {
        status: EContainerStatus.running,
        protected: true,
      };
      const protectedExited: IContainerActionTarget = {
        status: EContainerStatus.exited,
        protected: true,
      };

      expect(canExecuteContainerCommand(protectedRunning, 'stop')).toBe(false);
      expect(canExecuteContainerCommand(protectedRunning, 'restart')).toBe(
        false,
      );
      expect(canExecuteContainerCommand(protectedRunning, 'kill')).toBe(false);
      expect(canExecuteContainerCommand(protectedRunning, 'pause')).toBe(false);
      expect(canExecuteContainerCommand(protectedExited, 'start')).toBe(false);
      expect(canExecuteContainerCommand(protectedExited, 'restart')).toBe(
        false,
      );
    });

    it('should correctly evaluate start command', () => {
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.created },
          'start',
        ),
      ).toBe(true);
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.exited },
          'start',
        ),
      ).toBe(true);
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.running },
          'start',
        ),
      ).toBe(false);
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.paused },
          'start',
        ),
      ).toBe(false);
    });

    it('should correctly evaluate stop command', () => {
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.running },
          'stop',
        ),
      ).toBe(true);
      expect(
        canExecuteContainerCommand({ status: EContainerStatus.paused }, 'stop'),
      ).toBe(true);
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.restarting },
          'stop',
        ),
      ).toBe(true);
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.created },
          'stop',
        ),
      ).toBe(false);
      expect(
        canExecuteContainerCommand({ status: EContainerStatus.exited }, 'stop'),
      ).toBe(false);
      expect(
        canExecuteContainerCommand({ status: EContainerStatus.dead }, 'stop'),
      ).toBe(false);
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.removing },
          'stop',
        ),
      ).toBe(false);
    });

    it('should correctly evaluate restart command', () => {
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.running },
          'restart',
        ),
      ).toBe(true);
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.exited },
          'restart',
        ),
      ).toBe(true);
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.paused },
          'restart',
        ),
      ).toBe(true);
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.created },
          'restart',
        ),
      ).toBe(false);
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.removing },
          'restart',
        ),
      ).toBe(false);
    });

    it('should correctly evaluate kill command', () => {
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.running },
          'kill',
        ),
      ).toBe(true);
      expect(
        canExecuteContainerCommand({ status: EContainerStatus.paused }, 'kill'),
      ).toBe(true);
      expect(
        canExecuteContainerCommand({ status: EContainerStatus.exited }, 'kill'),
      ).toBe(false);
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.created },
          'kill',
        ),
      ).toBe(false);
    });

    it('should correctly evaluate pause command', () => {
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.running },
          'pause',
        ),
      ).toBe(true);
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.paused },
          'pause',
        ),
      ).toBe(false);
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.exited },
          'pause',
        ),
      ).toBe(false);
    });

    it('should correctly evaluate unpause command', () => {
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.paused },
          'unpause',
        ),
      ).toBe(true);
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.running },
          'unpause',
        ),
      ).toBe(false);
      expect(
        canExecuteContainerCommand(
          { status: EContainerStatus.exited },
          'unpause',
        ),
      ).toBe(false);
    });
  });

  describe('filterContainersForCommand', () => {
    const list: IContainerActionTarget[] = [
      { status: EContainerStatus.running, protected: false },
      { status: EContainerStatus.exited, protected: false },
      { status: EContainerStatus.running, protected: true },
      { status: EContainerStatus.paused, protected: false },
    ];

    it('should return empty array for null or empty list', () => {
      expect(filterContainersForCommand(null, 'start')).toEqual([]);
      expect(filterContainersForCommand([], 'start')).toEqual([]);
    });

    it('should filter containers applicable for start', () => {
      const result = filterContainersForCommand(list, 'start');
      expect(result).toEqual([
        { status: EContainerStatus.exited, protected: false },
      ]);
    });

    it('should filter containers applicable for stop, ignoring protected', () => {
      const result = filterContainersForCommand(list, 'stop');
      expect(result).toEqual([
        { status: EContainerStatus.running, protected: false },
        { status: EContainerStatus.paused, protected: false },
      ]);
    });

    it('should filter containers applicable for restart', () => {
      const result = filterContainersForCommand(list, 'restart');
      expect(result).toEqual([
        { status: EContainerStatus.running, protected: false },
        { status: EContainerStatus.exited, protected: false },
        { status: EContainerStatus.paused, protected: false },
      ]);
    });
  });
});
