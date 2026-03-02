import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  resource,
  signal,
} from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { ActivatedRoute } from '@angular/router';
import { catchError, firstValueFrom, map, of } from 'rxjs';
import { ToastService } from 'src/app/core/services/toast.service';
import { ContainersApiService } from 'src/app/features/containers/containers-api.service';
import {
  EContainerHealthSeverity,
  EContainerStatusSeverity,
  IContainerInfo,
  IContainerPatchBody,
} from 'src/app/features/containers/containers.interface';
import { AccordionModule } from 'primeng/accordion';
import { TranslatePipe } from '@ngx-translate/core';
import { Location } from '@angular/common';
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
import { ContainerCardInspectComponent } from './container-card-inspect/container-card-inspect.component';
import { DayjsPipe } from '@shared/pipes/dayjs.pipe';

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
    ContainerCardInspectComponent,
    DayjsPipe,
  ],
  templateUrl: './container-card.component.html',
  styleUrl: './container-card.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainerCardComponent {
  private readonly activatedRoute = inject(ActivatedRoute);
  private readonly toastService = inject(ToastService);
  private readonly containersApiService = inject(ContainersApiService);
  private readonly location = inject(Location);

  protected readonly hostId = toSignal(
    this.activatedRoute.params.pipe(map((params) => Number(params.hostId) || null)),
  );
  protected readonly containerNameOrId = toSignal(
    this.activatedRoute.params.pipe(map((params) => params.containerNameOrId)),
  );

  protected readonly info = resource({
    loader: () => {
      const hostId = this.hostId();
      const containerNameOrId = this.containerNameOrId();
      return firstValueFrom(
        this.containersApiService.get(hostId, containerNameOrId).pipe(
          catchError((error) => {
            this.toastService.error(error);
            return of(null);
          }),
        ),
      );
    },
  });

  protected readonly EContainerStatusSeverity = EContainerStatusSeverity;
  protected readonly EContainerHealthSeverity = EContainerHealthSeverity;
  /**
   * Value of opened accordion items
   */
  protected readonly accordionValue = signal<string | number | string[] | number[]>('general');
  /**
   * General info
   */
  protected readonly item = computed(() => {
    const info = this.info.value();
    if (info?.item) {
      return info.item;
    }
    return null;
  });
  /**
   * Ports value
   */
  protected readonly itemPorts = computed(() => {
    const item = this.item();
    let ports: string = '';
    if (item.ports) {
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
   * Navigate back
   */
  protected goBack(): void {
    this.location.back();
  }

  protected patchContainer(body: IContainerPatchBody): void {
    const item = this.item();
    this.containersApiService.patch(item.host_id, item.name, body).subscribe({
      next: (res) => {
        this.info.update((info) => ({
          ...info,
          ...res,
        }));
      },
      error: (error) => {
        this.toastService.error(error);
        this.info.reload();
      },
    });
  }

  protected onControlDone(info: IContainerInfo): void {
    this.info.set(info);
    setTimeout(() => {
      this.info.reload();
    }, 5000);
  }
}
