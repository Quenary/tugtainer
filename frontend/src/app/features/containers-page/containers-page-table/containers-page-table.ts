import { NgTemplateOutlet, KeyValuePipe, DatePipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, DestroyRef, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { MenuItem, MessageService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { InputTextModule } from 'primeng/inputtext';
import { ProgressBarModule } from 'primeng/progressbar';
import { SkeletonModule } from 'primeng/skeleton';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ToggleButtonModule } from 'primeng/togglebutton';
import { distinctUntilChanged, finalize, map, repeat, takeWhile } from 'rxjs';
import { ContainersApiService } from 'src/app/entities/containers/containers-api.service';
import {
  ECheckStatus,
  EContainerStatus,
  IContainer,
  IContainerPatchBody,
} from 'src/app/entities/containers/containers-interface';
import { parseError } from 'src/app/shared/functions/parse-error.function';
import { NaiveDatePipe } from 'src/app/shared/pipes/naive-date.pipe';
import { Tooltip } from 'primeng/tooltip';
import { MenuModule } from 'primeng/menu';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import { SplitButtonModule } from 'primeng/splitbutton';

type TContainer = IContainer & {
  splitButtonMenu: MenuItem[];
  checkStatus?: ECheckStatus;
};

@Component({
  selector: 'app-containers-page-table',
  imports: [
    TableModule,
    TranslateModule,
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
  ],
  templateUrl: './containers-page-table.html',
  styleUrl: './containers-page-table.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ContainersPageTable {
  private readonly containersApiService = inject(ContainersApiService);
  private readonly messageService = inject(MessageService);
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
  private readonly menuTranslates = this.translateService.instant('CONTAINERS.TABLE.C_MENU');

  public readonly isLoading = signal<boolean>(false);
  public readonly list = signal<Array<TContainer>>([]);

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
          const _list = list.map((item) => {
            const splitButtonMenu: MenuItem[] = [
              {
                label: this.menuTranslates.UPDATE,
                command: () => this.checkContainer(item.name, true),
                disabled: !item.update_available,
                ...(item.update_available
                  ? { badge: 'available', badgeStyleClass: 'p-badge-success' }
                  : {}),
              },
            ];
            return { ...item, splitButtonMenu };
          });
          this.list.set(_list);
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
          this.messageService.add({
            severity: 'success',
            summary: this.translateService.instant('GENERAL.SUCCESS'),
          });
          const list = this.list();
          const index = list.findIndex((item) => item.name == container.name);
          list[index] = {
            ...list[index],
            ...container,
          };
          this.list.set([...list]);
        },
        error: (error) => {
          this.messageService.add({
            severity: 'error',
            summary: this.translateService.instant('GENERAL.ERROR'),
            detail: parseError(error),
          });
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
          this.watchCheckProgress(id, name);
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

  private watchCheckProgress(id: string, name: string): void {
    this.containersApiService
      .getCheckProgress(id)
      .pipe(
        repeat({ delay: 500 }),
        map(res => res?.status),
        distinctUntilChanged(),
        takeWhile((status) => ![ECheckStatus.DONE, ECheckStatus.ERROR].includes(status), true),
        takeUntilDestroyed(this.destroyRef),
      )
      .subscribe({
        next: (status) => {
          const list = this.list();
          const index = list.findIndex((item) => [id, name].includes(item.name));
          if (index > -1) {
            const _list = [...list];
            _list[index] = {
              ...list[index],
              checkStatus: status,
            };
            this.list.set(_list);
          }
        },
        complete: () => {
          this.updateList();
        },
      });
  }
}
