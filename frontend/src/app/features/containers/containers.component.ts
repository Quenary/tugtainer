import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  effect,
  inject,
  signal,
} from '@angular/core';
import { ContainersTableComponent } from './containers-table/containers-table.component';
import { AccordionModule } from 'primeng/accordion';
import { TagModule } from 'primeng/tag';
import { ButtonModule } from 'primeng/button';
import { RouterLink } from '@angular/router';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { NoHostsComponent } from '@shared/components/no-hosts/no-hosts.component';
import { WithHostsListDirective } from '@shared/directives/with-hosts-list.directive';
import { ToolbarModule } from 'primeng/toolbar';
import { EActionStatus, IAllActionProgress } from '@shared/interfaces/progress.interface';
import { ContainersApiService } from 'src/app/features/containers/containers-api.service';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { DialogModule } from 'primeng/dialog';
import { HostCheckResultComponent } from '@shared/components/host-check-result/host-check-result.component';
import { SettingsApiService } from 'src/app/features/settings/settings-api.service';

const onlyAvailableStorageKey = 'tugtainer-containers-only-available';

@Component({
  selector: 'app-containers',
  imports: [
    ContainersTableComponent,
    AccordionModule,
    TagModule,
    ButtonModule,
    RouterLink,
    TranslatePipe,
    NoHostsComponent,
    ToolbarModule,
    DialogModule,
    HostCheckResultComponent,
  ],
  templateUrl: './containers.component.html',
  styleUrl: './containers.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainersComponent extends WithHostsListDirective {
  private readonly containersApiService = inject(ContainersApiService);
  private readonly destroyRef = inject(DestroyRef);
  private readonly translateService = inject(TranslateService);
  private readonly settingsApiService = inject(SettingsApiService);

  protected readonly checkAllProgress = signal<IAllActionProgress>(null);
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
      ![EActionStatus.DONE, EActionStatus.ERROR].includes(checkAllProgress.status)
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
          .watchProgress<IAllActionProgress>(cache_id)
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
