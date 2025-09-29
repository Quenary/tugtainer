import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  output,
  signal,
} from '@angular/core';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { ProgressBarModule } from 'primeng/progressbar';
import { TagModule } from 'primeng/tag';
import { finalize, repeat, takeWhile } from 'rxjs';
import { ContainersApiService } from 'src/app/entities/containers/containers-api.service';
import { ECheckStatus, ICheckProgress } from 'src/app/entities/containers/containers-interface';
import { parseError } from 'src/app/shared/functions/parse-error.function';

@Component({
  selector: 'app-containers-page-header',
  imports: [ButtonModule, ProgressBarModule, TranslateModule, TagModule],
  templateUrl: './containers-page-header.html',
  styleUrl: './containers-page-header.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainersPageHeader {
  private readonly containersApiService = inject(ContainersApiService);
  private readonly messageService = inject(MessageService);
  private readonly translateService = inject(TranslateService);
  private readonly destroyRef = inject(DestroyRef);

  public readonly onDone = output();

  public readonly ECheckStatus = ECheckStatus;
  public readonly checkProgress = signal<ICheckProgress>(null);
  private readonly _isLoading = signal<boolean>(false);
  public readonly isLoading = computed(() => {
    const checkProgress = this.checkProgress();
    const isLoading = this._isLoading();
    return isLoading || (!!checkProgress && checkProgress.status !== ECheckStatus.DONE);
  });

  public checkAndUpdate(): void {
    this._isLoading.set(true);
    this.containersApiService
      .checkAll()
      .pipe(
        finalize(() => {
          this._isLoading.set(false);
        }),
      )
      .subscribe({
        next: (id) => {
          this.watchCheckProgress(id);
          this.messageService.add({
            severity: 'success',
            summary: this.translateService.instant('GENERAL.IN_PROGRESS'),
          });
        },
        error: (error) => {
          this.messageService.add({
            severity: 'error',
            summary: this.translateService.instant('GENERAL.ERROR'),
            detail: parseError(error),
          });
        },
      });
  }

  private watchCheckProgress(id: string): void {
    this.containersApiService
      .getCheckProgress(id)
      .pipe(
        repeat({ delay: 500 }),
        takeWhile((res) => ![ECheckStatus.DONE, ECheckStatus.ERROR].includes(res.status), true),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (res) => {
          this.checkProgress.set(res);
        },
        complete: () => {
          this.onDone.emit();
        },
      });
  }
}
