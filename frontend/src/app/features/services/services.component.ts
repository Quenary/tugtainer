import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { ServicesTableComponent } from './services-table/services-table.component';
import { ServicesStore } from './services.store';

@Component({
  selector: 'app-services',
  imports: [ServicesTableComponent],
  templateUrl: './services.component.html',
  styleUrl: './services.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ServicesComponent {
  protected readonly servicesStore = inject(ServicesStore);
}
