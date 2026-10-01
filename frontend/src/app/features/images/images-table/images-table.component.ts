import { DecimalPipe } from '@angular/common';
import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { TranslatePipe } from '@ngx-translate/core';
import { ConfirmationService } from '@openng/optimus-ui/api';
import { Button } from '@openng/optimus-ui/button';
import { IconField } from '@openng/optimus-ui/iconfield';
import { InputIcon } from '@openng/optimus-ui/inputicon';
import { InputText } from '@openng/optimus-ui/inputtext';
import { TableModule } from '@openng/optimus-ui/table';
import { Tag } from '@openng/optimus-ui/tag';
import { Toolbar } from '@openng/optimus-ui/toolbar';
import { Tooltip } from '@openng/optimus-ui/tooltip';
import { DayjsPipe } from '@shared/pipes/dayjs.pipe';
import { ImagesStore } from '../images.store';
import { RouterLink } from '@angular/router';

@Component({
  selector: 'app-images-table',
  imports: [
    TableModule,
    Button,
    TranslatePipe,
    Tag,
    IconField,
    InputText,
    InputIcon,
    DayjsPipe,
    Tooltip,
    DecimalPipe,
    FormsModule,
    Toolbar,
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
