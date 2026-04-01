import { inject, Injectable } from '@angular/core';
import { TranslateService } from '@ngx-translate/core';
import { BehaviorSubject, map, Observable } from 'rxjs';
import { EStorageKey } from 'src/app/app.enums';

export type Theme = 'app-auto' | 'app-light' | 'app-dark';
export interface ITheme {
  value: Theme;
  label: string;
  icon: string;
}

@Injectable({
  providedIn: 'root',
})
export class AppThemeService {
  private readonly translateService = inject(TranslateService);

  private readonly _theme$ = new BehaviorSubject<Theme | null>(null);
  public get theme$(): Observable<Theme | null> {
    return this._theme$.asObservable();
  }
  public readonly themes$: Observable<ITheme[]> = this.translateService
    .getStreamOnTranslationChange('THEMES')
    .pipe(
      map((t) => [
        { value: 'app-auto', label: t['AUTO'], icon: 'pi pi-heart' },
        { value: 'app-light', label: t['LIGHT'], icon: 'pi pi-sun' },
        { value: 'app-dark', label: t['DARK'], icon: 'pi pi-moon' },
      ]),
    );

  public init(): void {
    const theme: Theme =
      localStorage.getItemJson<Theme>(EStorageKey.THEME) ?? 'app-auto';
    this.setTheme(theme);
  }

  public setTheme(theme: Theme): void {
    this._theme$.next(theme);
    localStorage.setItemJson(EStorageKey.THEME, theme);
    if (theme == 'app-auto') {
      const isDarkMode =
        window.matchMedia &&
        window.matchMedia('(prefers-color-scheme: dark)').matches;
      theme = isDarkMode ? 'app-dark' : 'app-light';
    }
    document.documentElement.className = theme;
  }
}
