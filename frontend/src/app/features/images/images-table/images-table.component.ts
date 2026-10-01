import { DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { ConfirmationService } from '@openng/optimus-ui/api';
import { ButtonModule } from '@openng/optimus-ui/button';
import { DialogModule } from '@openng/optimus-ui/dialog';
import { IconFieldModule } from '@openng/optimus-ui/iconfield';
import { InputIconModule } from '@openng/optimus-ui/inputicon';
import { InputTextModule } from '@openng/optimus-ui/inputtext';
import { TableModule } from '@openng/optimus-ui/table';
import { TagModule } from '@openng/optimus-ui/tag';
import { ToggleSwitchModule } from '@openng/optimus-ui/toggleswitch';
import { ToolbarModule } from '@openng/optimus-ui/toolbar';
import { TooltipModule } from '@openng/optimus-ui/tooltip';
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
