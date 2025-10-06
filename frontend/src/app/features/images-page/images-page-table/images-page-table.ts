import { DatePipe, DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { ConfirmationService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { ButtonGroupModule } from 'primeng/buttongroup';
import { ConfirmPopup } from 'primeng/confirmpopup';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { InputTextModule } from 'primeng/inputtext';
import { ProgressBarModule } from 'primeng/progressbar';
import { SplitButtonModule } from 'primeng/splitbutton';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { finalize } from 'rxjs';
import { ToastService } from 'src/app/core/services/toast.service';
import { ImagesApiService } from 'src/app/entities/images/images-api.service';
import { IImage } from 'src/app/entities/images/images-interface';

@Component({
  selector: 'app-images-page-table',
  imports: [
    TableModule,
    ButtonModule,
    TranslatePipe,
    TagModule,
    ProgressBarModule,
    IconFieldModule,
    InputTextModule,
    InputIconModule,
    SplitButtonModule,
    ConfirmPopup,
    ButtonGroupModule,
    DatePipe,
    TooltipModule,
    DecimalPipe,
  ],
  providers: [ConfirmationService],
  templateUrl: './images-page-table.html',
  styleUrl: './images-page-table.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImagesPageTable {
  private readonly imagesApiService = inject(ImagesApiService);
  private readonly toastService = inject(ToastService);
  private readonly translateService = inject(TranslateService);
  private readonly confirmationService = inject(ConfirmationService);

  public readonly isLoading = signal<boolean>(false);
  public readonly list = signal<IImage[]>([]);

  constructor() {
    this.updateList();
  }

  public updateList(): void {
    this.isLoading.set(true);
    this.imagesApiService
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

  public confirmPrune($event: Event) {
    this.confirmationService.confirm({
      target: $event.currentTarget,
      message: this.translateService.instant('IMAGES.TABLE.PRUNE_CONFIRM'),
      rejectButtonProps: {
        label: this.translateService.instant('GENERAL.CANCEL'),
        severity: 'secondary',
        outlined: true,
      },
      acceptButtonProps: {
        label: this.translateService.instant('GENERAL.CONFIRM'),
        severity: 'warn',
      },
      accept: () => {
        this.prune();
      },
    });
  }

  private prune(): void {
    this.isLoading.set(true);
    this.imagesApiService
      .prune()
      .pipe(
        finalize(() => {
          this.isLoading.set(false);
        }),
      )
      .subscribe({
        next: (res) => {
          const reclaimed = res.SpaceReclaimed.toFixed(2).replace('.00', '');
          const detail = this.translateService.instant('IMAGES.TABLE.PRUNE_SPACE_RECLAIMED', {
            value: reclaimed,
          });
          this.toastService.success(this.translateService.instant('GENERAL.SUCCESS'), detail);
          this.updateList();
        },
        error: (error) => {
          this.toastService.error(error);
        },
      });
  }
}
