import { DecimalPipe, NgStyle } from '@angular/common';
import {
  ChangeDetectionStrategy,
  Component,
  inject,
  linkedSignal,
  model,
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
import { BooleanFieldComponent } from '@shared/components/boolean-field/boolean-field.component';
import { DayjsPipe } from '@shared/pipes/dayjs.pipe';
import { ImagesStore } from '../images.store';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-images-table',
  imports: [
    TableModule,
    ButtonModule,
    TranslatePipe,
    TagModule,
    IconFieldModule,
    InputTextModule,
    InputIconModule,
    ConfirmPopup,
    DayjsPipe,
    TooltipModule,
    DecimalPipe,
    DialogModule,
    ToggleSwitchModule,
    FormsModule,
    NgStyle,
    ToolbarModule,
    BooleanFieldComponent,
    RouterLink,
  ],
  providers: [ConfirmationService],
  templateUrl: './images-table.component.html',
  styleUrl: './images-table.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImagesTableComponent {
  private readonly translateService = inject(TranslateService);
  private readonly confirmationService = inject(ConfirmationService);
  protected readonly imagesStore = inject(ImagesStore);

  /**
   * Prune all flag for confirmation popup toggle
   */
  protected readonly pruneAll = model<boolean>(false);
  /**
   * If prune results dialog visible
   */
  protected readonly pruneDialogVisible = linkedSignal<boolean>(
    () => !!this.imagesStore.pruneResult(),
  );

  constructor() {
    this.imagesStore.loadList();
  }

  protected confirmPrune($event: Event): void {
    this.confirmationService.confirm({
      target: $event.currentTarget,
      message: this.translateService.instant('IMAGES.PRUNE_CONFIRM'),
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
        this.imagesStore.prune({
          body: {
            all: this.pruneAll(),
          },
        });
      },
    });
  }
}
