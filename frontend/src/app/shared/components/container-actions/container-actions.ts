import {
  booleanAttribute,
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { ButtonModule } from 'primeng/button';
import { ButtonGroupModule } from 'primeng/buttongroup';
import { TooltipModule } from 'primeng/tooltip';
import { finalize } from 'rxjs';
import { ToastService } from 'src/app/core/services/toast.service';
import { ContainersApiService } from 'src/app/entities/containers/containers-api.service';
import {
  IContainerInfo,
  IContainerListItem,
  TControlContainerCommand,
} from 'src/app/entities/containers/containers-interface';
import { IGroupCheckProgressCache } from 'src/app/entities/progress-cache/progress-cache.interface';

/**
 * Container action buttons and common logic
 */
@Component({
  selector: 'app-container-actions',
  imports: [ButtonGroupModule, ButtonModule, TranslatePipe, TooltipModule],
  templateUrl: './container-actions.html',
  styleUrl: './container-actions.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainerActions {
  private readonly containersApiService = inject(ContainersApiService);
  private readonly toastService = inject(ToastService);
  private readonly translateService = inject(TranslateService);
  private readonly destroyRef = inject(DestroyRef);

  /**
   * Container item
   */
  public readonly item = input.required<IContainerListItem>();
  /**
   * Whether to show container control buttons
   * @default false
   */
  public readonly withControl = input(false, { transform: booleanAttribute });
  /**
   * Continuos progress events
   */
  public readonly onProgress = output<IGroupCheckProgressCache>();
  /**
   * Last progress event
   */
  public readonly onDone = output<void>();
  /**
   * Container control result event
   */
  public readonly onControlDone = output<IContainerInfo>();

  /**
   * Loading flag
   */
  protected readonly loading = signal<'check' | 'update' | 'command'>(null);
  /**
   * Whether to show container control buttons (internal)
   */
  protected readonly showControlButtons = computed<boolean>(() => {
    const item = this.item();
    const withCommands = this.withControl();
    return withCommands && !!item && !item.protected;
  });
  /**
   * Container cannot be updated
   */
  protected readonly cantUpdate = computed<boolean>(() => {
    const item = this.item();
    return !item.update_available || item.status != 'running' || item.protected;
  });
  /**
   * Whether to show update button tooltip
   */
  protected readonly showUpdateTooltip = computed<boolean>(() => {
    const item = this.item();
    return item.update_available && (item.status != 'running' || item.protected);
  });

  /**
   * Run check/update process
   * @param update
   * @returns
   */
  protected check(update: boolean): void {
    const item = this.item();
    if (!item) {
      return;
    }
    this.loading.set(update ? 'update' : 'check');
    this.containersApiService.checkContainer(item.host_id, item.name, update).subscribe({
      next: (cache_id) => {
        this.toastService.success(this.translateService.instant('GENERAL.IN_PROGRESS'));
        this.containersApiService
          .watchProgress(cache_id)
          .pipe(
            finalize(() => {
              this.loading.set(null);
            }),
            takeUntilDestroyed(this.destroyRef),
          )
          .subscribe({
            next: (res) => {
              this.onProgress.emit(res);
            },
            complete: () => {
              this.onDone.emit();
            },
          });
      },
    });
  }

  protected controlContainer(command: TControlContainerCommand): void {
    const item = this.item();
    this.loading.set('command');
    this.containersApiService
      .controlContainer(item.host_id, command, item.container_id)
      .pipe(finalize(() => this.loading.set(null)))
      .subscribe({
        next: (result) => {
          this.onControlDone.emit(result);
        },
        error: (error) => {
          this.toastService.error(error, this.translateService.instant('GENERAL.ERROR'));
        },
      });
  }
}
