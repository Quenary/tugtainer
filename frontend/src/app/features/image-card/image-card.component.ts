import {
  ChangeDetectionStrategy,
  Component,
  inject,
  OnDestroy,
  signal,
} from '@angular/core';
import { InspectComponent } from '@shared/components/inspect/inspect.component';
import { ImagesStore } from '../images/images.store';
import { ActivatedRoute } from '@angular/router';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
import {
  AccordionPanel,
  AccordionHeader,
  AccordionContent,
  Accordion,
} from '@openng/optimus-ui/accordion';
import { TranslatePipe } from '@ngx-translate/core';
import { Toolbar } from '@openng/optimus-ui/toolbar';
import { Button } from '@openng/optimus-ui/button';
import { Tag } from '@openng/optimus-ui/tag';
import { ImageCardGeneralComponent } from './image-card-general/image-card-general.component';

@Component({
  selector: 'app-image-card',
  imports: [
    InspectComponent,
    AccordionPanel,
    AccordionHeader,
    AccordionContent,
    Accordion,
    TranslatePipe,
    Toolbar,
    Button,
    Tag,
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
   * Value of opened accordion items
   */
  protected readonly accordionValue = signal<
    string | number | string[] | number[]
  >('general');

  constructor() {
    this.activatedRoute.params
      .pipe(takeUntilDestroyed())
      .subscribe((params) => {
        this.imagesStore.select(params['imageId']);
        this.imagesStore.loadSelected();
      });
  }

  ngOnDestroy(): void {
    this.imagesStore.select(null);
  }
}
