import { EContainerStatus } from '../../features/containers/containers.interface';
import {
  canExecuteContainerCommand,
  filterContainersForCommand,
  IContainerActionTarget,
} from './container-action-rules.function';

describe('containerActionRules', () => {
  describe('canExecuteContainerCommand', () => {
    describe('guards', () => {
      it('rejects a missing container', () => {
        expect(canExecuteContainerCommand(null, 'start')).toBe(false);
        expect(canExecuteContainerCommand(undefined, 'stop')).toBe(false);
      });

      it('rejects a protected container', () => {
        const protectedRunning: IContainerActionTarget = {
          status: EContainerStatus.running,
          protected: true,
        };
        const protectedExited: IContainerActionTarget = {
          status: EContainerStatus.exited,
          protected: true,
        };

        expect(canExecuteContainerCommand(protectedRunning, 'stop')).toBe(
          false,
        );
        expect(canExecuteContainerCommand(protectedRunning, 'restart')).toBe(
          false,
        );
        expect(canExecuteContainerCommand(protectedRunning, 'kill')).toBe(
          false,
        );
        expect(canExecuteContainerCommand(protectedRunning, 'pause')).toBe(
          false,
        );
        expect(canExecuteContainerCommand(protectedExited, 'start')).toBe(
          false,
        );
        expect(canExecuteContainerCommand(protectedExited, 'restart')).toBe(
          false,
        );
      });
    });

    describe('start', () => {
      it('allows created', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.created },
            'start',
          ),
        ).toBe(true);
      });

      it('allows exited', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.exited },
            'start',
          ),
        ).toBe(true);
      });

      it('rejects running', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.running },
            'start',
          ),
        ).toBe(false);
      });

      it('rejects paused', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.paused },
            'start',
          ),
        ).toBe(false);
      });
    });

    describe('stop', () => {
      it('allows running', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.running },
            'stop',
          ),
        ).toBe(true);
      });

      it('allows paused', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.paused },
            'stop',
          ),
        ).toBe(true);
      });

      it('allows restarting', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.restarting },
            'stop',
          ),
        ).toBe(true);
      });

      it('rejects created', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.created },
            'stop',
          ),
        ).toBe(false);
      });

      it('rejects exited', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.exited },
            'stop',
          ),
        ).toBe(false);
      });

      it('rejects dead', () => {
        expect(
          canExecuteContainerCommand({ status: EContainerStatus.dead }, 'stop'),
        ).toBe(false);
      });

      it('rejects removing', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.removing },
            'stop',
          ),
        ).toBe(false);
      });
    });

    describe('restart', () => {
      it('allows running', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.running },
            'restart',
          ),
        ).toBe(true);
      });

      it('allows exited', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.exited },
            'restart',
          ),
        ).toBe(true);
      });

      it('allows paused', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.paused },
            'restart',
          ),
        ).toBe(true);
      });

      it('rejects created', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.created },
            'restart',
          ),
        ).toBe(false);
      });

      it('rejects removing', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.removing },
            'restart',
          ),
        ).toBe(false);
      });
    });

    describe('kill', () => {
      it('allows running', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.running },
            'kill',
          ),
        ).toBe(true);
      });

      it('allows paused', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.paused },
            'kill',
          ),
        ).toBe(true);
      });

      it('rejects exited', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.exited },
            'kill',
          ),
        ).toBe(false);
      });

      it('rejects created', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.created },
            'kill',
          ),
        ).toBe(false);
      });
    });

    describe('pause', () => {
      it('allows running', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.running },
            'pause',
          ),
        ).toBe(true);
      });

      it('rejects paused', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.paused },
            'pause',
          ),
        ).toBe(false);
      });

      it('rejects exited', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.exited },
            'pause',
          ),
        ).toBe(false);
      });
    });

    describe('unpause', () => {
      it('allows paused', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.paused },
            'unpause',
          ),
        ).toBe(true);
      });

      it('rejects running', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.running },
            'unpause',
          ),
        ).toBe(false);
      });

      it('rejects exited', () => {
        expect(
          canExecuteContainerCommand(
            { status: EContainerStatus.exited },
            'unpause',
          ),
        ).toBe(false);
      });
    });
  });

  describe('filterContainersForCommand', () => {
    const list: IContainerActionTarget[] = [
      { status: EContainerStatus.running, protected: false },
      { status: EContainerStatus.exited, protected: false },
      { status: EContainerStatus.running, protected: true },
      { status: EContainerStatus.paused, protected: false },
    ];

    it('returns an empty array without containers', () => {
      expect(filterContainersForCommand(null, 'start')).toEqual([]);
      expect(filterContainersForCommand([], 'start')).toEqual([]);
    });

    it('keeps containers that can start', () => {
      expect(filterContainersForCommand(list, 'start')).toEqual([
        { status: EContainerStatus.exited, protected: false },
      ]);
    });

    it('keeps containers that can stop and skips protected ones', () => {
      expect(filterContainersForCommand(list, 'stop')).toEqual([
        { status: EContainerStatus.running, protected: false },
        { status: EContainerStatus.paused, protected: false },
      ]);
    });

    it('keeps containers that can restart', () => {
      expect(filterContainersForCommand(list, 'restart')).toEqual([
        { status: EContainerStatus.running, protected: false },
        { status: EContainerStatus.exited, protected: false },
        { status: EContainerStatus.paused, protected: false },
      ]);
    });
  });
});
