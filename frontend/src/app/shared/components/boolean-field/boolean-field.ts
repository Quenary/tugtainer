import { ChangeDetectionStrategy, Component } from '@angular/core';

/**
 * Common wrapper for switch/checkbox + label
 */
@Component({
  selector: 'app-boolean-field',
  imports: [],
  templateUrl: './boolean-field.html',
  styleUrl: './boolean-field.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BooleanField {

}
