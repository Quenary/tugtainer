import { ChangeDetectionStrategy, Component, signal } from '@angular/core';
import { ImagesTableComponent } from './images-table/images-table.component';
import { RouterOutlet } from '@angular/router';

@Component({
  selector: 'app-images',
  imports: [ImagesTableComponent, RouterOutlet],
  templateUrl: './images.component.html',
  styleUrl: './images.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImagesComponent {
  protected readonly showTable = signal<boolean>(true);
}
