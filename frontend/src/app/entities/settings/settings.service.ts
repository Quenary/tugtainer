import { Injectable, signal } from '@angular/core';
import { ISetting } from './settings-interface';

/**
 * TODO add ngrx instead of this crutch
 */
@Injectable({
  providedIn: 'root',
})
export class SettingsService {
  public readonly settings = signal<ISetting[]>([]);
}
