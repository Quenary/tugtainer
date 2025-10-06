import { NgTemplateOutlet, KeyValuePipe, DatePipe } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  computed,
  DestroyRef,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { MenuItem } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { InputTextModule } from 'primeng/inputtext';
import { ProgressBarModule } from 'primeng/progressbar';
import { SkeletonModule } from 'primeng/skeleton';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ToggleButtonModule } from 'primeng/togglebutton';
import { finalize, Observable, repeat, takeWhile } from 'rxjs';
import { ContainersApiService } from 'src/app/entities/containers/containers-api.service';
import {
  ECheckStatus,
  EContainerStatus,
  ICheckProgress,
  IContainer,
  IContainerPatchBody,
} from 'src/app/entities/containers/containers-interface';
import { NaiveDatePipe } from 'src/app/shared/pipes/naive-date.pipe';
import { Tooltip } from 'primeng/tooltip';
import { MenuModule } from 'primeng/menu';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { SplitButtonModule } from 'primeng/splitbutton';
import { FieldsetModule } from 'primeng/fieldset';
import { ToastService } from 'src/app/core/services/toast.service';

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
    ProgressBarModule,
    TagModule,
    SkeletonModule,
    ButtonModule,
    IconFieldModule,
    InputTextModule,
    InputIconModule,
    NaiveDatePipe,
    DatePipe,
    Tooltip,
    MenuModule,
    SplitButtonModule,
    FieldsetModule,
  ],
  templateUrl: './containers-page-table.html',
  styleUrl: './containers-page-table.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainersPageTable {
  private readonly containersApiService = inject(ContainersApiService);
  private readonly toastService = inject(ToastService);
  private readonly translateService = inject(TranslateService);
  private readonly destroyRef = inject(DestroyRef);

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

  public readonly checkAllProgress = signal<ICheckProgress>(null);
  public readonly headerButtonMenu = computed<MenuItem[]>(() => {
    const checkAllProgress = this.checkAllProgress();
    const checkStatus = checkAllProgress?.status;
    const translates = this.translateService.instant('CONTAINERS.TABLE.HEADER_BUTTON_MENU');
    return [
      {
        label: translates.CHECK_ALL,
        command: () => this.checkAll(),
        disabled: checkStatus && ![ECheckStatus.DONE, ECheckStatus.ERROR].includes(checkStatus),
      },
    ];
  });

  constructor() {
    this.updateList();
  }

  public updateList(): void {
    this.isLoading.set(true);
    this.containersApiService
      .list()
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
    this.isLoading.set(true);
    this.containersApiService
      .patch(name, body)
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
    this.isLoading.set(true);
    const req$ = update
      ? this.containersApiService.updateContainer(name)
      : this.containersApiService.checkContainer(name);
    req$
      .pipe(
        finalize(() => {
          this.isLoading.set(false);
        }),
      )
      .subscribe({
        next: (id) => {
          this.toastService.success(this.translateService.instant('GENERAL.IN_PROGRESS'));
          this.watchCheckProgress(id).subscribe({
            next: (res) => {
              const status = res.status;
              const list = this.list();
              const index = list.findIndex((item) => [id, name].includes(item.name));
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

  public checkAll(): void {
    this.isLoading.set(true);
    this.containersApiService
      .checkAll()
      .pipe(
        finalize(() => {
          this.isLoading.set(false);
        }),
      )
      .subscribe({
        next: (id) => {
          this.toastService.success(this.translateService.instant('GENERAL.IN_PROGRESS'));
          this.watchCheckProgress(id).subscribe({
            next: (res) => {
              this.checkAllProgress.set(res);
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

  /**
   * Watch check progress
   * @param id id of progress cache
   * @returns
   */
  private watchCheckProgress(id: string): Observable<ICheckProgress> {
    return this.containersApiService.getCheckProgress(id).pipe(
      repeat({ delay: 500 }),
      takeWhile((res) => ![ECheckStatus.DONE, ECheckStatus.ERROR].includes(res?.status), true),
      takeUntilDestroyed(this.destroyRef),
    );
  }
}
