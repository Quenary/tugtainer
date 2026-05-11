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
import { HostCheckResultComponent } from '@shared/components/host-check-result/host-check-result.component';
import { ContainersStore, IContainerEntity } from '../containers.store';
import { ButtonGroupModule } from 'primeng/buttongroup';

const onlyAvailableStorageKey = 'tugtainer-containers-only-available';

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
    HostCheckResultComponent,
    ButtonGroupModule,
  ],
  templateUrl: './containers-table.component.html',
  styleUrl: './containers-table.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainersTableComponent {
  protected readonly containersStore = inject(ContainersStore);

  protected readonly EContainerStatusSeverity = EContainerStatusSeverity;
  protected readonly EContainerHealthSeverity = EContainerHealthSeverity;

  /**
   * Show only available filter
   */
  protected readonly onlyAvailable = signal<boolean>(
    localStorage.getItemJson(onlyAvailableStorageKey) ?? false,
  );
  /**
   * List of containers
   */
  protected readonly filteredList = computed(() => {
    const onlyAvailable = this.onlyAvailable();
    const entities = this.containersStore.entities();
    return onlyAvailable
      ? entities.filter((c) => c.update_available)
      : entities;
  });

  constructor() {
    effect(() => {
      const onlyAvailable = this.onlyAvailable();
      localStorage.setItemJson(onlyAvailableStorageKey, onlyAvailable);
    });
    this.containersStore.loadList();
  }

  protected onCheckEnabledChange(
    check_enabled: boolean,
    container: IContainerListItem,
  ): void {
    this.containersStore.patchContainer({
      id: container.id,
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
      id: container.id,
      body: {
        update_enabled,
      },
    });
  }

  protected onCheck(container: IContainerEntity): void {
    this.containersStore.checkContainer({ id: container.id });
  }

  protected onUpdate(container: IContainerEntity): void {
    this.containersStore.updateContainer({ id: container.id });
  }

  protected onCommand(
    command: TControlContainerCommand,
    container: IContainerEntity,
  ): void {
    this.containersStore.controlContainer({ id: container.id, command });
  }
}
