import { ChangeDetectionStrategy, Component } from '@angular/core';

/**
 * Common wrapper for switch/checkbox + label
 */
@Component({
  selector: 'app-boolean-field',
  imports: [],
  templateUrl: './boolean-field.component.html',
  styleUrl: './boolean-field.component.scss',
  changeDetection: ChangeDetectionStrategy.OnPush,
})
export class BooleanFieldComponent {}
