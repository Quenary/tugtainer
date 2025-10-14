import { NgTemplateOutlet, KeyValuePipe, DatePipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  input,
  OnInit,
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
import { finalize, Observable, repeat, takeWhile } from 'rxjs';
import { ContainersApiService } from 'src/app/entities/containers/containers-api.service';
import {
  ECheckStatus,
  EContainerStatus,
  IContainer,
  IContainerCheckData,
  IContainerPatchBody,
  IHostCheckData,
} from 'src/app/entities/containers/containers-interface';
import { NaiveDatePipe } from 'src/app/shared/pipes/naive-date.pipe';
import { Tooltip } from 'primeng/tooltip';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { FieldsetModule } from 'primeng/fieldset';
import { ToastService } from 'src/app/core/services/toast.service';
import { ButtonGroup } from 'primeng/buttongroup';
import { DialogModule } from 'primeng/dialog';
import { IHostInfo } from 'src/app/entities/hosts/hosts-interface';

type TContainer = IContainer & {
  checkStatus?: ECheckStatus;
};

@Component({
  selector: 'app-containers-page-table',
  imports: [
    TableModule,
    TranslatePipe,
    NgTemplateOutlet,
    KeyValuePipe,
    ToggleButtonModule,
    FormsModule,
    TagModule,
    ButtonModule,
    IconFieldModule,
    InputTextModule,
    InputIconModule,
    NaiveDatePipe,
    DatePipe,
    Tooltip,
    FieldsetModule,
    ButtonGroup,
    DialogModule,
  ],
  templateUrl: './containers-page-table.html',
  styleUrl: './containers-page-table.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainersPageTable implements OnInit {
  private readonly containersApiService = inject(ContainersApiService);
  private readonly toastService = inject(ToastService);
  private readonly translateService = inject(TranslateService);
  private readonly destroyRef = inject(DestroyRef);

  public readonly host = input.required<IHostInfo>();

  public readonly EContainerStatusSeverity: { [K in keyof typeof EContainerStatus]: string } = {
    [EContainerStatus.created]: 'primary',
    [EContainerStatus.paused]: 'contrast',
    [EContainerStatus.running]: 'success',
    [EContainerStatus.restarting]: 'info',
    [EContainerStatus.removing]: 'warn',
    [EContainerStatus.exited]: 'danger',
    [EContainerStatus.dead]: 'danger',
  };
  public readonly ECheckStatus = ECheckStatus;
  public readonly EContainerHealthSevirity = {
    healthy: 'success',
    unhealthy: 'danger',
  };

  public readonly isLoading = signal<boolean>(false);
  public readonly list = signal<Array<TContainer>>([]);

  public readonly checkHostProgress = signal<IHostCheckData>(null);
  public readonly checkAllActive = computed(() => {
    const checkAllProgress = this.checkHostProgress();
    return (
      checkAllProgress && ![ECheckStatus.DONE, ECheckStatus.ERROR].includes(checkAllProgress.status)
    );
  });
  public readonly checkAllDialogVisible = signal<boolean>(false);

  ngOnInit(): void {
    this.updateList();
  }

  public updateList(): void {
    const host = this.host();
    if (!host || !host.enabled) {
      return;
    }
    this.isLoading.set(true);
    this.containersApiService
      .list(host.id)
      .pipe(
        finalize(() => {
          this.isLoading.set(false);
        }),
      )
      .subscribe({
        next: (list) => {
          this.list.set(list);
        },
        error: (error) => {
          this.toastService.error(error);
        },
      });
  }

  public onCheckEnabledChange(check_enabled: boolean, container: IContainer): void {
    this.patchContainer(container.name, { check_enabled });
  }

  public onUpdateEnabledChange(update_enabled: boolean, container: IContainer): void {
    this.patchContainer(container.name, { update_enabled });
  }

  private patchContainer(name: string, body: IContainerPatchBody): void {
    const host = this.host();
    if (!host || !host.enabled) {
      return;
    }
    this.isLoading.set(true);
    this.containersApiService
      .patch(host.id, name, body)
      .pipe(
        finalize(() => {
          this.isLoading.set(false);
        }),
      )
      .subscribe({
        next: (container) => {
          this.toastService.success();
          const list = this.list();
          const index = list.findIndex((item) => item.name == container.name);
          list[index] = {
            ...list[index],
            ...container,
          };
          this.list.set([...list]);
        },
        error: (error) => {
          this.toastService.error(error);
          this.updateList();
        },
      });
  }

  public checkContainer(name: string, update: boolean = false): void {
    const host = this.host();
    if (!host || !host.enabled) {
      return;
    }
    this.isLoading.set(true);
    this.containersApiService
      .checkContainer(host.id, name, update)
      .pipe(
        finalize(() => {
          this.isLoading.set(false);
        }),
      )
      .subscribe({
        next: (cache_id) => {
          this.toastService.success(this.translateService.instant('GENERAL.IN_PROGRESS'));
          this.watchCheckProgress(cache_id).subscribe({
            next: (res) => {
              const status = res.status;
              const list = this.list();
              const index = list.findIndex((item) => item.name == name);
              if (index > -1) {
                const _list = [...list];
                _list[index].checkStatus = status;
                this.list.set(_list);
              }
            },
            complete: () => {
              this.updateList();
            },
          });
        },
        error: (error) => {
          this.toastService.error(error);
        },
      });
  }

  public checkHost(update: boolean = false): void {
    const host = this.host();
    if (!host || !host.enabled) {
      return;
    }
    this.isLoading.set(true);
    this.containersApiService
      .checkHost(host.id, update)
      .pipe(
        finalize(() => {
          this.isLoading.set(false);
        }),
      )
      .subscribe({
        next: (cache_id: string) => {
          this.toastService.success(this.translateService.instant('GENERAL.IN_PROGRESS'));
          this.watchCheckProgress<IHostCheckData>(cache_id).subscribe({
            next: (res) => {
              this.checkHostProgress.set(res);
            },
            complete: () => {
              this.updateList();
              this.checkAllDialogVisible.set(true);
            },
          });
        },
        error: (error) => {
          this.toastService.error(error);
        },
      });
  }

  /**
   * Watch check progress
   * @param id id of progress cache
   * @returns
   */
  private watchCheckProgress<T extends IContainerCheckData>(id: string): Observable<T> {
    return this.containersApiService.progress<T>(id).pipe(
      repeat({ delay: 500 }),
      takeWhile((res) => ![ECheckStatus.DONE, ECheckStatus.ERROR].includes(res?.status), true),
      takeUntilDestroyed(this.destroyRef),
    );
  }
}
