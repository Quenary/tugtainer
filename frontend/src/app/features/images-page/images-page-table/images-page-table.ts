import { DatePipe, DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject, input, OnInit, signal } from '@angular/core';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { ConfirmationService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { ButtonGroupModule } from 'primeng/buttongroup';
import { ConfirmPopup } from 'primeng/confirmpopup';
import { DialogModule } from 'primeng/dialog';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { InputTextModule } from 'primeng/inputtext';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { TooltipModule } from 'primeng/tooltip';
import { finalize } from 'rxjs';
import { ToastService } from 'src/app/core/services/toast.service';
import { IHostInfo } from 'src/app/entities/hosts/hosts-interface';
import { ImagesApiService } from 'src/app/entities/images/images-api.service';
import { IImage } from 'src/app/entities/images/images-interface';

@Component({
  selector: 'app-images-page-table',
  imports: [
    TableModule,
    ButtonModule,
    TranslatePipe,
    TagModule,
    IconFieldModule,
    InputTextModule,
    InputIconModule,
    ConfirmPopup,
    ButtonGroupModule,
    DatePipe,
    TooltipModule,
    DecimalPipe,
    DialogModule,
  ],
  providers: [ConfirmationService],
  templateUrl: './images-page-table.html',
  styleUrl: './images-page-table.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImagesPageTable implements OnInit {
  private readonly imagesApiService = inject(ImagesApiService);
  private readonly toastService = inject(ToastService);
  private readonly translateService = inject(TranslateService);
  private readonly confirmationService = inject(ConfirmationService);

  public readonly host = input.required<IHostInfo>();

  public readonly isLoading = signal<boolean>(false);
  public readonly pruneResult = signal<string>(null);
  public readonly list = signal<IImage[]>([]);

  ngOnInit(): void {
    this.updateList();
  }

  public updateList(): void {
    const host = this.host();
    this.isLoading.set(true);
    this.imagesApiService
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
        severity: 'danger',
      },
      accept: () => {
        this.prune();
      },
    });
  }

  private prune(): void {
    const host = this.host();
    this.isLoading.set(true);
    this.imagesApiService
      .prune(host.id)
      .pipe(
        finalize(() => {
          this.isLoading.set(false);
        }),
      )
      .subscribe({
        next: (res) => {
          this.pruneResult.set(res);
          this.updateList();
        },
        error: (error) => {
          this.toastService.error(error);
        },
      });
  }
}
