import {
  booleanAttribute,
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  output,
} from '@angular/core';
import { TranslatePipe } from '@ngx-translate/core';
import { ButtonModule } from 'primeng/button';
import { ButtonGroupModule } from 'primeng/buttongroup';
import { TooltipModule } from 'primeng/tooltip';
import { TControlContainerCommand } from 'src/app/features/containers/containers.interface';
import { ESettingKey } from 'src/app/features/settings/settings.interface';
import {
  IContainerEntity,
  TContainerEntityLoading,
} from 'src/app/features/containers/containers.store';
import { SettingsStore } from 'src/app/features/settings/settings.store';
import { IHostEntity } from 'src/app/features/hosts/hosts.store';

/**
 * Container action buttons and common logic
 */
@Component({
  selector: 'app-container-actions',
  imports: [ButtonGroupModule, ButtonModule, TranslatePipe, TooltipModule],
  templateUrl: './container-actions.component.html',
  styleUrl: './container-actions.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainerActionsComponent {
  private readonly settingsStore = inject(SettingsStore);

  /**
   * Container item
   */
  public readonly item = input.required<IContainerEntity>();
  /**
   * Current host
   */
  public readonly host = input.required<IHostEntity>();
  /**
   * Whether to show container control buttons
   * @default false
   */
  public readonly withControl = input(false, { transform: booleanAttribute });
  /**
   * Check button click
   */
  public readonly OnCheck = output<void>();
  /**
   * Update button click
   */
  public readonly OnUpdate = output<void>();
  /**
   * Container control result event
   */
  public readonly OnCommand = output<TControlContainerCommand>();

  /**
   * Whether to show container control buttons (internal)
   */
  protected readonly showControlButtons = computed<boolean>(() => {
    const item = this.item();
    const withCommands = this.withControl();
    return withCommands && !!item && !item.protected;
  });
  protected loading = computed<TContainerEntityLoading>(() => {
    const item = this.item();
    return item?.loading ?? null;
  });
  protected readonly hostActionLoading = computed<boolean>(() => {
    const host = this.host();
    return ['check', 'update', 'prune'].includes(host?.loading);
  });
  /**
   * Whether to update only running containers
   */
  protected readonly updateOnlyRunning = computed<boolean>(() => {
    const settings = this.settingsStore.entityMap();
    return (
      (settings[ESettingKey.UPDATE_ONLY_RUNNING]?.value as boolean) ?? true
    );
  });
  /**
   * Container cannot be updated
   */
  protected readonly cantUpdate = computed<boolean>(() => {
    const item = this.item();
    const updateOnlyRunning = this.updateOnlyRunning();
    if (!item) return true;
    return (
      !item.update_available ||
      item.protected ||
      (item.status != 'running' && updateOnlyRunning)
    );
  });
  /**
   * Whether to show update button tooltip
   */
  protected readonly showUpdateTooltip = computed<boolean>(() => {
    const item = this.item();
    const updateOnlyRunning = this.updateOnlyRunning();
    if (!item) return false;
    return (
      item.update_available &&
      ((item.status != 'running' && updateOnlyRunning) || item.protected)
    );
  });
}
