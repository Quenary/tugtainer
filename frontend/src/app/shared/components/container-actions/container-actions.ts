import {
  ChangeDetectionStrategy,
  Component,
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
import { finalize } from 'rxjs';
import { ToastService } from 'src/app/core/services/toast.service';
import { ContainersApiService } from 'src/app/entities/containers/containers-api.service';
import { IContainerListItem } from 'src/app/entities/containers/containers-interface';
import { IGroupCheckProgressCache } from 'src/app/entities/progress-cache/progress-cache.interface';

/**
 * Container action buttons and common logic
 */
@Component({
  selector: 'app-container-actions',
  imports: [ButtonGroupModule, ButtonModule, TranslatePipe],
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
   * Continuos progress events
   */
  public readonly onProgress = output<IGroupCheckProgressCache>();
  /**
   * Last progress event
   */
  public readonly onDone = output<void>();
  /**
   * Loading flag
   */
  protected readonly loading = signal<'check' | 'update'>(null);

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
}
