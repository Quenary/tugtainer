import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnDestroy,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import {
  EContainerHealthSeverity,
  EContainerStatusSeverity,
  IContainerPatchBody,
  TControlContainerCommand,
} from 'src/app/features/containers/containers.interface';
import { AccordionModule } from 'primeng/accordion';
import { TranslatePipe } from '@ngx-translate/core';
import { IftaLabelModule } from 'primeng/iftalabel';
import { InputTextModule } from 'primeng/inputtext';
import { TextareaModule } from 'primeng/textarea';
import { ToolbarModule } from 'primeng/toolbar';
import { ButtonModule } from 'primeng/button';
import { ToggleButtonModule } from 'primeng/togglebutton';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { ContainerActionsComponent } from '@shared/components/container-actions/container-actions.component';
import { ToggleSwitchModule } from 'primeng/toggleswitch';
import { FormsModule } from '@angular/forms';
import { ContainerCardLogsComponent } from './container-card-logs/container-card-logs.component';
import { BooleanFieldComponent } from '@shared/components/boolean-field/boolean-field.component';
import { DayjsPipe } from '@shared/pipes/dayjs.pipe';
import { ContainersStore } from '../containers/containers.store';
import { InspectComponent } from '@shared/components/inspect/inspect.component';

@Component({
  selector: 'app-container-card',
  imports: [
    AccordionModule,
    TranslatePipe,
    IftaLabelModule,
    InputTextModule,
    TextareaModule,
    ToolbarModule,
    ButtonModule,
    ToggleButtonModule,
    TagModule,
    TooltipModule,
    ContainerActionsComponent,
    ToggleSwitchModule,
    FormsModule,
    ContainerCardLogsComponent,
    BooleanFieldComponent,
    DayjsPipe,
    InspectComponent,
  ],
  templateUrl: './container-card.component.html',
  styleUrl: './container-card.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainerCardComponent implements OnDestroy {
  private readonly activatedRoute = inject(ActivatedRoute);
  protected readonly containersStore = inject(ContainersStore);

  protected readonly EContainerStatusSeverity = EContainerStatusSeverity;
  protected readonly EContainerHealthSeverity = EContainerHealthSeverity;

  /**
   * Value of opened accordion items
   */
  protected readonly accordionValue = signal<
    string | number | string[] | number[]
  >('general');
  /**
   * Ports value
   */
  protected readonly itemPorts = computed(() => {
    const item = this.containersStore.selected();
    let ports = '';
    if (item?.ports) {
      for (const [key, binds] of Object.entries(item.ports)) {
        for (const bind of binds) {
          ports += `${key}:`;
          if (bind.HostIp) {
            ports += `${bind.HostIp}:`;
          }
          ports += `${bind.HostPort}\n`;
        }
      }
    }
    return ports;
  });
  /**
   * Ports textarea rows count
   */
  protected readonly itemPortsRows = computed<number>(() => {
    const itemPorts = this.itemPorts();
    return itemPorts.split('\n').length;
  });
  /**
   * Container inspect object
   */
  protected readonly inspect = computed(
    () => this.containersStore.selectedInfo()?.inspect,
  );

  constructor() {
    this.activatedRoute.params
      .pipe(takeUntilDestroyed())
      .subscribe((params) => {
        this.containersStore.select(params['containerNameOrId']);
        this.containersStore.loadSelected();
      });
  }

  ngOnDestroy(): void {
    this.containersStore.select(null);
  }

  protected patchContainer(body: IContainerPatchBody): void {
    const c = this.containersStore.selected();
    this.containersStore.patchContainer({
      containerName: c.name,
      body,
    });
  }

  protected onCheck(): void {
    const c = this.containersStore.selected();
    this.containersStore.checkContainer({ containerName: c.name });
  }

  protected onUpdate(): void {
    const c = this.containersStore.selected();
    this.containersStore.updateContainer({ containerName: c.name });
  }

  protected onCommand(command: TControlContainerCommand): void {
    const c = this.containersStore.selected();
    this.containersStore.controlContainer({ containerName: c.name, command });
  }
}
