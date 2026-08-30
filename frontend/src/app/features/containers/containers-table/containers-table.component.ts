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
import { ButtonModule } from 'primeng/button';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { InputTextModule } from 'primeng/inputtext';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ToggleButtonModule } from 'primeng/togglebutton';
import {
  IContainerListItem,
  EContainerStatus,
  EContainerStatusSeverity,
  EContainerHealthSeverity,
  TControlContainerCommand,
} from 'src/app/features/containers/containers.interface';
import { Tooltip } from 'primeng/tooltip';
import { FieldsetModule } from 'primeng/fieldset';
import { DialogModule } from 'primeng/dialog';
import { RouterLink } from '@angular/router';
import { ToolbarModule } from 'primeng/toolbar';
import { ContainerActionsComponent } from '@shared/components/container-actions/container-actions.component';
import { ContainersStore, IContainerEntity } from '../containers.store';
import { ButtonGroupModule } from 'primeng/buttongroup';
import { MultiSelectModule } from 'primeng/multiselect';
import { SettingsStore } from 'src/app/features/settings/settings.store';
import { ESettingKey } from 'src/app/features/settings/settings.interface';

const onlyAvailableStorageKey = 'tugtainer-containers-only-available';
const statusesStorageKey = 'tugtainer-containers-statuses';

@Component({
  selector: 'app-containers-table',
  imports: [
    TableModule,
    TranslatePipe,
    ToggleButtonModule,
    FormsModule,
    TagModule,
    ButtonModule,
    IconFieldModule,
    InputTextModule,
    InputIconModule,
    Tooltip,
    FieldsetModule,
    DialogModule,
    RouterLink,
    ToolbarModule,
    ContainerActionsComponent,
    ButtonGroupModule,
    MultiSelectModule,
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
}
