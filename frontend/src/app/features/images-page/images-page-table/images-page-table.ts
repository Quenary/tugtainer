import { DatePipe, DecimalPipe, NgStyle } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  inject,
  input,
  model,
  resource,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslatePipe, TranslateService } from '@ngx-translate/core';
import { ConfirmationService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { ConfirmPopup } from 'primeng/confirmpopup';
import { DialogModule } from 'primeng/dialog';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { InputTextModule } from 'primeng/inputtext';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ToggleSwitchModule } from 'primeng/toggleswitch';
import { ToolbarModule } from 'primeng/toolbar';
import { TooltipModule } from 'primeng/tooltip';
import { catchError, finalize, firstValueFrom, of } from 'rxjs';
import { ToastService } from 'src/app/core/services/toast.service';
import { IHostInfo } from 'src/app/entities/hosts/hosts-interface';
import { ImagesApiService } from 'src/app/entities/images/images-api.service';
import { IImage, IPruneImageRequestBodySchema } from 'src/app/entities/images/images-interface';

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
    DatePipe,
    TooltipModule,
    DecimalPipe,
    DialogModule,
    ToggleSwitchModule,
    FormsModule,
    NgStyle,
    ToolbarModule,
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

  /**
   * Host info
   */
  public readonly host = input.required<IHostInfo>();

  /**
   * List of images
   */
  protected readonly list = resource<IImage[], { host: IHostInfo }>({
    params: () => ({
      host: this.host(),
    }),
    loader: (params) => {
      const host = params.params.host;
      if (!host || !host.enabled) {
        return Promise.resolve([]);
      }
      return firstValueFrom(
        this.imagesApiService.list(host.id).pipe(
          catchError((error) => {
            this.toastService.error(error);
            return of([]);
          }),
        ),
      );
    },
    defaultValue: [],
  });
  /**
   * Prune in progress flag
   */
  protected readonly pruneInProgress = signal<boolean>(false);
  /**
   * Prune result
   */
  protected readonly pruneResult = signal<string>(null);
  /**
   * Prune all flag for confirmation popup toggle
   */
  protected readonly pruneAll = model<boolean>(false);

  protected confirmPrune($event: Event) {
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
    this.pruneInProgress.set(true);
    const host = this.host();
    const body: IPruneImageRequestBodySchema = {
      all: this.pruneAll(),
    };
    this.imagesApiService
      .prune(host.id, body)
      .pipe(
        finalize(() => {
          this.pruneInProgress.set(false);
        }),
      )
      .subscribe({
        next: (res) => {
          this.pruneResult.set(res);
          this.list.reload();
        },
        error: (error) => {
          this.toastService.error(error);
          this.list.reload();
        },
      });
  }
}
