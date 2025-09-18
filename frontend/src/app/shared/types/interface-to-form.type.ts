import { AbstractControl } from '@angular/forms';

export type TInterfaceToForm<T> = {
  [K in keyof T]: AbstractControl<T[K]>;
};
