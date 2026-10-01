import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ImagesStore } from '../../images/images.store';
import { TranslatePipe } from '@ngx-translate/core';
import { Tag } from '@openng/optimus-ui/tag';
import { IftaLabel } from '@openng/optimus-ui/iftalabel';
import { Textarea } from '@openng/optimus-ui/textarea';
import { InputText } from '@openng/optimus-ui/inputtext';
import { DecimalPipe } from '@angular/common';
import { DayjsPipe } from '@shared/pipes/dayjs.pipe';

@Component({
  selector: 'app-image-card-general',
  imports: [
    TranslatePipe,
    Tag,
    IftaLabel,
    Textarea,
    InputText,
    DecimalPipe,
    DayjsPipe,
  ],
  templateUrl: './image-card-general.component.html',
  styleUrl: './image-card-general.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImageCardGeneralComponent {
  protected readonly imagesStore = inject(ImagesStore);
}
