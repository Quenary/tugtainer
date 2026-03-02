import { ChangeDetectionStrategy, Component } from '@angular/core';
import { ImagesTableComponent } from './images-table/images-table.component';
import { RouterLink } from '@angular/router';
import { TranslatePipe } from '@ngx-translate/core';
import { AccordionModule } from 'primeng/accordion';
import { ButtonModule } from 'primeng/button';
import { TagModule } from 'primeng/tag';
import { NoHostsComponent } from 'src/app/shared/components/no-hosts/no-hosts.component';
import { WithHostsListDirective } from 'src/app/shared/directives/with-hosts-list.directive';

@Component({
  selector: 'app-images',
  imports: [
    ImagesTableComponent,
    AccordionModule,
    TagModule,
    ButtonModule,
    RouterLink,
    TranslatePipe,
    NoHostsComponent,
  ],
  templateUrl: './images.component.html',
  styleUrl: './images.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImagesComponent extends WithHostsListDirective {
  constructor() {
    super();
    this.accordionValueStorageKey.set('tugtainer-images-accordion-value');
  }
}
