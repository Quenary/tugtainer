import { ChangeDetectorRef, inject, Pipe, PipeTransform } from '@angular/core';
import dayjs, { ConfigType } from 'dayjs';
import dayjsLocalizedFormat from 'dayjs/plugin/localizedFormat';
import dayjsLocaleData from 'dayjs/plugin/localeData';
import { LocaleService } from 'src/app/core/services/locale.service';
import { takeUntilDestroyed } from '@angular/core/rxjs-interop';
dayjs.extend(dayjsLocalizedFormat);
dayjs.extend(dayjsLocaleData);

@Pipe({
  name: 'dayjs',
  pure: false,
})
export class DayjsPipe implements PipeTransform {
  private readonly localeService = inject(LocaleService);
  private readonly changeDetectorRef = inject(ChangeDetectorRef);

  transform(value: ConfigType, format = 'L LTS') {
    try {
      const djs = dayjs(value);
      if (djs.isValid()) {
        return djs.format(format);
      }
      return null;
    } catch (e) {
      console.warn(e);
      return null;
    }
  }

  constructor() {
    this.localeService.onChange$.pipe(takeUntilDestroyed()).subscribe(() => {
      this.changeDetectorRef.markForCheck();
    });
  }
}
