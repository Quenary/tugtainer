import { Pipe, PipeTransform } from '@angular/core';

/**
 * Pipe that prepares naive python date
 * to time aware date with Z at the end.
 */
@Pipe({
  name: 'naiveDate',
  pure: true,
  standalone: true,
})
export class NaiveDatePipe implements PipeTransform {
  transform(value: string): string {
    if (!value) {
      return value;
    }
    if (/\b([+-]\d{2}:\d{2}|Z)\b/.test(value)) {
      return value;
    }
    return value + 'Z';
  }
}
