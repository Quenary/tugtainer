import {
  ChangeDetectionStrategy,
  Component,
  effect,
  inject,
  OnDestroy,
  signal,
} from '@angular/core';
import { InspectComponent } from '@shared/components/inspect/inspect.component';
import { ImagesStore } from '../images/images.store';
import { ActivatedRoute } from '@angular/router';
import { toSignal } from '@angular/core/rxjs-interop';
import { map } from 'rxjs';
import { AccordionModule } from 'primeng/accordion';
import { TranslatePipe } from '@ngx-translate/core';
import { ToolbarModule } from 'primeng/toolbar';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { IftaLabelModule } from 'primeng/iftalabel';
import { TextareaModule } from 'primeng/textarea';
import { InputTextModule } from 'primeng/inputtext';
import { ImageCardGeneralComponent } from './image-card-general/image-card-general.component';

@Component({
  selector: 'app-image-card',
  imports: [
    InspectComponent,
    AccordionModule,
    TranslatePipe,
    ToolbarModule,
    ButtonModule,
    TagModule,
    IftaLabelModule,
    TextareaModule,
    InputTextModule,
    ImageCardGeneralComponent,
  ],
  templateUrl: './image-card.component.html',
  styleUrl: './image-card.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImageCardComponent implements OnDestroy {
  private readonly activatedRoute = inject(ActivatedRoute);
  protected readonly imagesStore = inject(ImagesStore);

  /**
   * Path parameter
   */
  protected readonly imageId = toSignal<string>(
    this.activatedRoute.params.pipe(map((params) => params.imageId)),
  );
  /**
   * Value of opened accordion items
   */
  protected readonly accordionValue = signal<
    string | number | string[] | number[]
  >('general');

  constructor() {
    effect(() => {
      const imageId = this.imageId();
      this.imagesStore.select(imageId);
      this.imagesStore.loadSelected();
    });
  }

  ngOnDestroy(): void {
    this.imagesStore.select(null);
  }
}
