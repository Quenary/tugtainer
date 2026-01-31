import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  signal,
} from '@angular/core';
import { ContainersPageTable } from './containers-page-table/containers-page-table';
import { AccordionModule } from 'primeng/accordion';
import { TagModule } from 'primeng/tag';
import { ButtonModule } from 'primeng/button';
import { RouterLink } from '@angular/router';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { NoHosts } from 'src/app/shared/components/no-hosts/no-hosts';
import { WithHostsList } from 'src/app/shared/directives/with-hosts-list';
import { ToolbarModule } from 'primeng/toolbar';
import {
  ECheckStatus,
  IAllCheckProgressCache,
} from 'src/app/entities/progress-cache/progress-cache.interface';
import { ContainersApiService } from 'src/app/entities/containers/containers-api.service';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DialogModule } from 'primeng/dialog';
import { HostCheckResult } from 'src/app/shared/components/host-check-result/host-check-result';
import { SettingsApiService } from 'src/app/entities/settings/settings-api.service';

const onlyAvailableStorageKey = 'tugtainer-containers-only-available';

@Component({
  selector: 'app-containers-page',
  imports: [
    ContainersPageTable,
    AccordionModule,
    TagModule,
    ButtonModule,
    RouterLink,
    TranslatePipe,
    NoHosts,
    ToolbarModule,
    DialogModule,
    HostCheckResult,
  ],
  templateUrl: './containers-page.html',
  styleUrl: './containers-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainersPage extends WithHostsList {
  private readonly containersApiService = inject(ContainersApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly translateService = inject(TranslateService);
  private readonly settingsApiService = inject(SettingsApiService);

  protected readonly checkAllProgress = signal<IAllCheckProgressCache>(null);
  protected readonly checkAllProgressResults = computed(() => {
    const checkAllProgress = this.checkAllProgress();
    return checkAllProgress?.result ? Object.values(checkAllProgress.result) : null;
  });
  protected readonly checkAllDisabled = computed(() => {
    const hosts = this.hosts.value() ?? [];
    return hosts.filter((h) => h.enabled).length == 0;
  });
  protected readonly checkAllActive = computed<boolean>(() => {
    const checkAllProgress = this.checkAllProgress();
    return (
      !!checkAllProgress &&
      ![ECheckStatus.DONE, ECheckStatus.ERROR].includes(checkAllProgress.status)
    );
  });
  protected readonly checkAllDialogVisible = signal<boolean>(false);
  /**
   * Show only available filter
   */
  protected readonly onlyAvailable = signal<boolean>(
    localStorage.getItemJson(onlyAvailableStorageKey) ?? false,
  );

  constructor() {
    super();
    this.accordionValueStorageKey.set('tugtainer-containers-accordion-value');
    effect(() => {
      const onlyAvailable = this.onlyAvailable();
      localStorage.setItemJson(onlyAvailableStorageKey, onlyAvailable);
    });
    this.settingsApiService.list().subscribe();
  }

  protected checkAllHosts(): void {
    this.containersApiService.checkAll().subscribe({
      next: (cache_id: string) => {
        this.toastService.success(this.translateService.instant('GENERAL.IN_PROGRESS'));
        this.containersApiService
          .watchProgress<IAllCheckProgressCache>(cache_id)
          .pipe(takeUntilDestroyed(this.destroyRef))
          .subscribe({
            next: (res) => {
              this.checkAllProgress.set(res);
            },
            complete: () => {
              this.hosts.reload();
              this.checkAllDialogVisible.set(true);
            },
          });
      },
      error: (error) => {
        this.toastService.error(error);
      },
    });
  }
}
