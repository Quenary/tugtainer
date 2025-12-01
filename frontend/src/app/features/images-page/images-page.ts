import { ChangeDetectionStrategy, Component } from '@angular/core';
import { ImagesPageTable } from './images-page-table/images-page-table';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { AccordionModule } from 'primeng/accordion';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { NoHosts } from 'src/app/shared/components/no-hosts/no-hosts';
import { WithHostsList } from 'src/app/shared/directives/with-hosts-list';

@Component({
  selector: 'app-images-page',
  imports: [
    ImagesPageTable,
    AccordionModule,
    TagModule,
    ButtonModule,
    RouterLink,
    TranslatePipe,
    NoHosts,
  ],
  templateUrl: './images-page.html',
  styleUrl: './images-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImagesPage extends WithHostsList {
  constructor() {
    super();
    this.accordionValueStorageKey.set('tugtainer-images-accordion-value');
  }
}
