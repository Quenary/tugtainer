import { DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { ConfirmationService } from 'primeng/api';
import { ButtonModule } from 'primeng/button';
import { DialogModule } from 'primeng/dialog';
import { IconFieldModule } from 'primeng/iconfield';
import { InputIconModule } from 'primeng/inputicon';
import { InputTextModule } from 'primeng/inputtext';
import { TableModule } from 'primeng/table';
import { TagModule } from 'primeng/tag';
import { ToggleSwitchModule } from 'primeng/toggleswitch';
import { ToolbarModule } from 'primeng/toolbar';
import { TooltipModule } from 'primeng/tooltip';
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
    DayjsPipe,
    TooltipModule,
    DecimalPipe,
    DialogModule,
    ToggleSwitchModule,
    FormsModule,
    ToolbarModule,
    RouterLink,
  ],
  providers: [ConfirmationService],
  templateUrl: './images-table.component.html',
  styleUrl: './images-table.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImagesTableComponent {
  protected readonly imagesStore = inject(ImagesStore);

  constructor() {
    this.imagesStore.loadList();
  }
}
