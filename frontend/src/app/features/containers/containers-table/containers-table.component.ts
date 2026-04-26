import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  input,
  resource,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { ButtonModule } from 'primeng/button';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { InputTextModule } from 'primeng/inputtext';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ToggleButtonModule } from 'primeng/togglebutton';
import { catchError, firstValueFrom, map, of } from 'rxjs';
import { ContainersApiService } from 'src/app/features/containers/containers-api.service';
import {
  IContainerListItem,
  IContainerPatchBody,
  EContainerStatusSeverity,
  EContainerHealthSeverity,
} from 'src/app/features/containers/containers.interface';
import { Tooltip } from 'primeng/tooltip';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FieldsetModule } from 'primeng/fieldset';
import { ToastService } from 'src/app/core/services/toast.service';
import { DialogModule } from 'primeng/dialog';
import { IHostInfo } from 'src/app/features/hosts/hosts.interface';
import { RouterLink } from '@angular/router';
import { ToolbarModule } from 'primeng/toolbar';
import { ContainerActionsComponent } from '@shared/components/container-actions/container-actions.component';
import {
  EActionStatus,
  IHostActionProgress,
} from '@shared/interfaces/progress.interface';
import { HostCheckResultComponent } from '@shared/components/host-check-result/host-check-result.component';

interface IListParams {
  host: IHostInfo;
  onlyAvailable: boolean;
}

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
  ],
  templateUrl: './containers-table.component.html',
  styleUrl: './containers-table.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainersTableComponent {
  private readonly containersApiService = inject(ContainersApiService);
  private readonly toastService = inject(ToastService);
  private readonly translateService = inject(TranslateService);
  private readonly destroyRef = inject(DestroyRef);

  /**
   * Host info
   */
  public readonly host = input.required<IHostInfo>();
  /**
   * Show only available filter
   */
  public readonly onlyAvailable = input<boolean>(false);

  protected readonly EContainerStatusSeverity = EContainerStatusSeverity;
  protected readonly EContainerHealthSeverity = EContainerHealthSeverity;

  /**
   * List of containers
   */
  protected readonly list = resource<IContainerListItem[], IListParams>({
    params: () => ({
      host: this.host(),
      onlyAvailable: this.onlyAvailable(),
    }),
    loader: (params) => {
      const host = params.params.host;
      const onlyAvailable = params.params.onlyAvailable;
      if (!host || !host.enabled) {
        return Promise.resolve([]);
      }
      return firstValueFrom(
        this.containersApiService.list(host.id).pipe(
          map((list) => {
            if (onlyAvailable) {
              return list.filter((item) => item.update_available);
            }
            return list;
          }),
          catchError((error) => {
            this.toastService.error(error);
            return of([]);
          }),
        ),
      );
    },
    defaultValue: [],
  });
  /**
   * Check host state
   */
  protected readonly checkHostProgress = signal<IHostActionProgress>(null);
  /**
   * Check host in progress flag
   */
  protected readonly checkHostActive = computed<boolean>(() => {
    const checkHostProgress = this.checkHostProgress();
    return (
      !!checkHostProgress &&
      ![EActionStatus.DONE, EActionStatus.ERROR].includes(
        checkHostProgress.status,
      )
    );
  });
  /**
   * Check host dialog visible flag
   */
  protected readonly checkHostDialogVisible = signal<boolean>(false);

  protected checkHost(update = false): void {
    const host = this.host();
    const req$ = update
      ? this.containersApiService.updateHost(host.id)
      : this.containersApiService.checkHost(host.id);
    req$.subscribe({
      next: (cache_id: string) => {
        this.toastService.success(
          this.translateService.instant('GENERAL.IN_PROGRESS'),
        );
        this.containersApiService
          .watchProgress<IHostActionProgress>(cache_id)
          .pipe(takeUntilDestroyed(this.destroyRef))
          .subscribe({
            next: (res) => {
              this.checkHostProgress.set(res);
            },
            complete: () => {
              this.list.reload();
              this.checkHostDialogVisible.set(true);
            },
          });
      },
      error: (error) => {
        this.toastService.error(error);
      },
    });
  }

  protected onCheckEnabledChange(
    check_enabled: boolean,
    container: IContainerListItem,
  ): void {
    this.patchContainer(container.name, { check_enabled });
  }

  protected onUpdateEnabledChange(
    update_enabled: boolean,
    container: IContainerListItem,
  ): void {
    this.patchContainer(container.name, { update_enabled });
  }

  private patchContainer(name: string, body: IContainerPatchBody): void {
    const host = this.host();
    this.containersApiService.patch(host.id, name, body).subscribe({
      next: (container) => {
        this.list.update((list) => {
          const index = list.findIndex((item) => item.name == container.name);
          list[index] = {
            ...list[index],
            ...container,
          };
          return [...list];
        });
      },
      error: (error) => {
        this.toastService.error(error);
        this.list.reload();
      },
    });
  }

  protected onContainerProgressDone(): void {
    this.list.reload();
  }
}
