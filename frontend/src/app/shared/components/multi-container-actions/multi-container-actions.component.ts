import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  output,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { TranslateService } from '@ngx-translate/core';
import { MenuItem } from 'primeng/api';
import { SplitButtonModule } from 'primeng/splitbutton';
import { TControlContainerCommand } from 'src/app/features/containers/containers.interface';
import { IContainerEntity } from 'src/app/features/containers/containers.store';
import { filterContainersForCommand } from '@shared/functions/container-action-rules.function';

export const MULTI_CONTAINER_COMMAND_ORDER: TControlContainerCommand[] = [
  'start',
  'stop',
  'restart',
  'pause',
  'unpause',
  'kill',
];

export const MULTI_CONTAINER_COMMAND_ICONS: Record<
  TControlContainerCommand,
  string
> = {
  start: 'pi pi-play',
  stop: 'pi pi-stop',
  restart: 'pi pi-sync',
  pause: 'pi pi-pause',
  unpause: 'pi pi-forward',
  kill: 'pi pi-ban',
};

@Component({
  selector: 'app-multi-container-actions',
  imports: [SplitButtonModule],
  templateUrl: './multi-container-actions.component.html',
  styleUrl: './multi-container-actions.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class MultiContainerActionsComponent {
  private readonly translateService = inject(TranslateService);

  /**
   * Selected containers list
   */
  public readonly containers = input<IContainerEntity[]>([]);

  /**
   * Whether action buttons are disabled externally
   */
  public readonly disabled = input<boolean>(false);

  /**
   * Action trigger event emitting command and filtered eligible containers
   */
  public readonly OnCommand = output<{
    command: TControlContainerCommand;
    containers: IContainerEntity[];
  }>();

  /**
   * Translations for container commands
   */
  private readonly commandTranslations = toSignal<object, object>(
    this.translateService.stream('CONTAINERS.COMMANDS'),
    { initialValue: {} },
  );

  /**
   * Map of valid target containers per command
   */
  protected readonly targetMap = computed<
    Record<TControlContainerCommand, IContainerEntity[]>
  >(() => {
    const list = this.containers();
    return {
      start: filterContainersForCommand(list, 'start'),
      stop: filterContainersForCommand(list, 'stop'),
      restart: filterContainersForCommand(list, 'restart'),
      pause: filterContainersForCommand(list, 'pause'),
      unpause: filterContainersForCommand(list, 'unpause'),
      kill: filterContainersForCommand(list, 'kill'),
    };
  });

  /**
   * Action that is applicable to the majority of selected containers
   */
  protected readonly majorityCommand = computed<TControlContainerCommand>(
    () => {
      const map = this.targetMap();
      let bestCmd: TControlContainerCommand = 'start';
      let maxCount = -1;

      for (const cmd of MULTI_CONTAINER_COMMAND_ORDER) {
        const count = map[cmd].length;
        if (count > maxCount) {
          maxCount = count;
          bestCmd = cmd;
        }
      }

      return bestCmd;
    },
  );

  /**
   * Main split button label
   */
  protected readonly mainLabel = computed<string>(() => {
    const cmd = this.majorityCommand();
    const map = this.targetMap();
    const t = this.commandTranslations();
    const name = t?.[cmd.toUpperCase()] ?? cmd;
    const count = map[cmd].length;
    return count > 0 ? `${name} (${count})` : name;
  });

  /**
   * Main split button icon
   */
  protected readonly mainIcon = computed<string>(() => {
    return MULTI_CONTAINER_COMMAND_ICONS[this.majorityCommand()];
  });

  /**
   * Dropdown menu items for remaining actions
   */
  protected readonly menuItems = computed<MenuItem[]>(() => {
    const main = this.majorityCommand();
    const map = this.targetMap();
    const trans = this.commandTranslations();

    return MULTI_CONTAINER_COMMAND_ORDER.filter((cmd) => cmd !== main).map(
      (cmd) => {
        const targets = map[cmd];
        const name = trans?.[cmd.toUpperCase()] ?? cmd;
        const label = targets.length > 0 ? `${name} (${targets.length})` : name;

        return {
          label,
          icon: MULTI_CONTAINER_COMMAND_ICONS[cmd],
          disabled: targets.length === 0,
          command: () => {
            this.OnCommand.emit({ command: cmd, containers: targets });
          },
        };
      },
    );
  });

  /**
   * Whether the split button is completely disabled
   */
  protected readonly isSplitButtonDisabled = computed<boolean>(() => {
    const disabled = this.disabled();
    const map = this.targetMap();
    const main = this.majorityCommand();
    if (disabled) return disabled;
    return map[main].length === 0;
  });

  /**
   * Primary button click handler
   */
  protected onMainButtonClick(): void {
    const main = this.majorityCommand();
    const targets = this.targetMap()[main];
    if (targets.length === 0) {
      return;
    }
    this.OnCommand.emit({ command: main, containers: targets });
  }
}
