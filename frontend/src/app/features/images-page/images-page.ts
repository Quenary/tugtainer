import { ChangeDetectionStrategy, Component } from '@angular/core';
import { ImagesPageTable } from './images-page-table/images-page-table';

@Component({
  selector: 'app-images-page',
  imports: [ImagesPageTable],
  templateUrl: './images-page.html',
  styleUrl: './images-page.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class ImagesPage {}
