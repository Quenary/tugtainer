import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ImagesStore } from '../../images/images.store';
import { TranslatePipe } from '@ngx-translate/core';
import { TagModule } from 'primeng/tag';
import { IftaLabelModule } from 'primeng/iftalabel';
import { TextareaModule } from 'primeng/textarea';
import { InputTextModule } from 'primeng/inputtext';
import { DecimalPipe } from '@angular/common';
import { DayjsPipe } from '@shared/pipes/dayjs.pipe';

@Component({
  selector: 'app-image-card-general',
  imports: [
    TranslatePipe,
    TagModule,
    IftaLabelModule,
    TextareaModule,
    InputTextModule,
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
