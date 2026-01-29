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
import { ContainersApiService } from 'src/app/entities/containers/containers-api.service';
import {
  EContainerHealthSeverity,
  EContainerStatusSeverity,
  IContainerInfo,
  IContainerPatchBody,
} from 'src/app/entities/containers/containers-interface';
import { TreeModule } from 'primeng/tree';
import { TreeNode } from 'primeng/api';
import { isPremitive } from 'src/app/shared/functions/is-premitive.function';
import { AccordionModule } from 'primeng/accordion';
import { TranslatePipe } from '@ngx-translate/core';
import { DatePipe, Location } from '@angular/common';
import { IftaLabelModule } from 'primeng/iftalabel';
import { InputTextModule } from 'primeng/inputtext';
import { NaiveDatePipe } from 'src/app/shared/pipes/naive-date.pipe';
import { TextareaModule } from 'primeng/textarea';
import { TabsModule } from 'primeng/tabs';
import { ToolbarModule } from 'primeng/toolbar';
import { ButtonModule } from 'primeng/button';
import { ToggleButtonModule } from 'primeng/togglebutton';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { ContainerActions } from 'src/app/shared/components/container-actions/container-actions';
import { ToggleSwitchModule } from 'primeng/toggleswitch';
import { FormsModule } from '@angular/forms';
import { ContainerCardLogs } from './container-card-logs/container-card-logs';

@Component({
  selector: 'app-container-card',
  imports: [
    TreeModule,
    AccordionModule,
    TranslatePipe,
    IftaLabelModule,
    InputTextModule,
    DatePipe,
    NaiveDatePipe,
    TextareaModule,
    TabsModule,
    ToolbarModule,
    ButtonModule,
    ToggleButtonModule,
    TagModule,
    TooltipModule,
    ContainerActions,
    ToggleSwitchModule,
    FormsModule,
    ContainerCardLogs,
  ],
  templateUrl: './container-card.html',
  styleUrl: './container-card.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainerCard {
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
   * Inspect json value
   */
  protected readonly inspectJson = computed(() => {
    const info = this.info.value();
    if (info?.inspect) {
      return JSON.stringify(info.inspect, null, 2).trim();
    }
    return null;
  });
  /**
   * Inspect tree value
   */
  protected readonly inspectTree = computed<TreeNode[]>(() => {
    const info = this.info.value();
    if (info?.inspect) {
      const root = this.getTree(info.inspect, 'root');
      return root.children;
    }
    return [];
  });

  private getTree(value: unknown, key: string): TreeNode {
    if (isPremitive(value)) {
      return {
        label: key != null ? `${key}: ${String(value)}` : String(value),
        data: value,
        leaf: true,
      };
    }

    if (Array.isArray(value)) {
      return {
        label: key != null ? key : 'Array',
        data: value,
        children: value.map((item, index) => {
          const child = this.getTree(item, index.toString());
          return child;
        }),
        leaf: value.length === 0,
      };
    }

    const children: TreeNode[] = Object.entries(value).map(([k, v]) => this.getTree(v, k));

    return {
      label: key,
      data: value,
      children,
      leaf: children.length === 0,
    };
  }

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
