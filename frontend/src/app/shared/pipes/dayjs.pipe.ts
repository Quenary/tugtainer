import { Pipe, PipeTransform } from '@angular/core';
import dayjs, { ConfigType } from 'dayjs';
import dayjsLocalizedFormat from 'dayjs/plugin/localizedFormat';
import dayjsLocaleData from 'dayjs/plugin/localeData';
dayjs.extend(dayjsLocalizedFormat);
dayjs.extend(dayjsLocaleData);

@Pipe({
  name: 'dayjs',
  pure: true,
})
export class DayjsPipe implements PipeTransform {
  transform(value: ConfigType, format: string = 'L LTS') {
    try {
      const djs = dayjs(value);
      if (djs.isValid()) {
        return djs.locale(navigator.language).format(format);
      }
      return null;
    } catch (e) {
      console.warn(e);
      return null;
    }
  }
}
