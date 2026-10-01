import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { Button } from '@openng/optimus-ui/button';
import { IconField } from '@openng/optimus-ui/iconfield';
import { InputIcon } from '@openng/optimus-ui/inputicon';
import { InputText } from '@openng/optimus-ui/inputtext';
import { TableModule } from '@openng/optimus-ui/table';
import { Tag } from '@openng/optimus-ui/tag';
import { ToggleButton } from '@openng/optimus-ui/togglebutton';
import {
  IContainerListItem,
  EContainerStatus,
  EContainerStatusSeverity,
  EContainerHealthSeverity,
  TControlContainerCommand,
} from 'src/app/features/containers/containers.interface';
import { Tooltip } from '@openng/optimus-ui/tooltip';
import { RouterLink } from '@angular/router';
import { Toolbar } from '@openng/optimus-ui/toolbar';
import { ContainerActionsComponent } from '@shared/components/container-actions/container-actions.component';
import { MultiContainerActionsComponent } from '@shared/components/multi-container-actions/multi-container-actions.component';
import { ContainersStore, IContainerEntity } from '../containers.store';
import { ButtonGroup } from '@openng/optimus-ui/buttongroup';
import { MultiSelect } from '@openng/optimus-ui/multiselect';
import { SettingsStore } from 'src/app/features/settings/settings.store';
import { ESettingKey } from 'src/app/features/settings/settings.interface';

const onlyAvailableStorageKey = 'tugtainer-containers-only-available';
const statusesStorageKey = 'tugtainer-containers-statuses';

@Component({
  selector: 'app-containers-table',
  imports: [
    TableModule,
    TranslatePipe,
    ToggleButton,
    FormsModule,
    Tag,
    Button,
    IconField,
    InputText,
    InputIcon,
    Tooltip,
    RouterLink,
    Toolbar,
    ContainerActionsComponent,
    MultiContainerActionsComponent,
    ButtonGroup,
    MultiSelect,
  ],
  templateUrl: './containers-table.component.html',
  styleUrl: './containers-table.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainersTableComponent {
  protected readonly containersStore = inject(ContainersStore);
  private readonly settingsStore = inject(SettingsStore);

  protected readonly EContainerStatusSeverity = EContainerStatusSeverity;
  protected readonly EContainerHealthSeverity = EContainerHealthSeverity;

  /**
   * Selected table rows
   */
  protected readonly selected = signal<IContainerEntity[]>([]);

  /**
   * Show only available filter
   */
  protected readonly onlyAvailable = signal<boolean>(
    localStorage.getItemJson(onlyAvailableStorageKey) ?? false,
  );
  /**
   * Options of the status filter
   */
  protected readonly statusOptions = Object.values(EContainerStatus);
  /**
   * Statuses filter, empty means no filtration
   */
  protected readonly statuses = signal<EContainerStatus[] | null | undefined>(
    localStorage.getItemJson<EContainerStatus[]>(statusesStorageKey),
  );
  /**
   * List of containers
   */
  protected readonly filteredList = computed(() => {
    const onlyAvailable = this.onlyAvailable();
    const statuses = this.statuses();
    const entities = this.containersStore.entities();
    return entities.filter(
      (c) =>
        (!onlyAvailable || c.update_available) &&
        (!statuses?.length || statuses.includes(c.status)),
    );
  });

  /**
   * Selected containers that can be updated
   */
  protected readonly updatableSelected = computed(() => {
    const updateOnlyRunning =
      (this.settingsStore.entityMap()[ESettingKey.UPDATE_ONLY_RUNNING]
        ?.value as boolean) ?? true;
    return this.selected().filter(
      (c) =>
        c.update_available &&
        !c.protected &&
        (c.status === 'running' || !updateOnlyRunning),
    );
  });

  constructor() {
    effect(() => {
      const onlyAvailable = this.onlyAvailable();
      localStorage.setItemJson(onlyAvailableStorageKey, onlyAvailable);
    });
    effect(() => {
      const statuses = this.statuses();
      localStorage.setItemJson(statusesStorageKey, statuses);
    });
    this.containersStore.loadList();
  }

  protected onCheckEnabledChange(
    check_enabled: boolean,
    container: IContainerListItem,
  ): void {
    this.containersStore.patchContainer({
      containerName: container.name,
      body: {
        check_enabled,
      },
    });
  }

  protected onUpdateEnabledChange(
    update_enabled: boolean,
    container: IContainerListItem,
  ): void {
    this.containersStore.patchContainer({
      containerName: container.name,
      body: {
        update_enabled,
      },
    });
  }

  protected onCheck(container: IContainerEntity): void {
    this.containersStore.checkContainer({ containerName: container.name });
  }

  protected onUpdate(container: IContainerEntity): void {
    this.containersStore.updateContainer({ containerName: container.name });
  }

  protected onCheckSelected(): void {
    const names = this.selected().map((c) => c.name);
    if (!names.length) {
      return;
    }
    this.containersStore.checkContainers({ names });
    this.selected.set([]);
  }

  protected onUpdateSelected(): void {
    const names = this.updatableSelected().map((c) => c.name);
    if (!names.length) {
      return;
    }
    this.containersStore.updateContainers({ names });
    this.selected.set([]);
  }

  protected onCommand(
    command: TControlContainerCommand,
    container: IContainerEntity,
  ): void {
    this.containersStore.controlContainer({
      containerName: container.name,
      command,
    });
  }

  protected onBulkCommand(event: {
    command: TControlContainerCommand;
    containers: IContainerEntity[];
  }): void {
    const names = event.containers.map((c) => c.name);
    if (!names.length) {
      return;
    }
    this.containersStore.controlContainers({
      names,
      command: event.command,
    });
    this.selected.set([]);
  }
}
