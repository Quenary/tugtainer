import { registerLocaleData } from '@angular/common';
import { Injectable } from '@angular/core';
import dayjs from 'dayjs';
import {
  defaultLang,
  supportedLangs,
  supportedLocales,
} from 'src/app/app.consts';
import { EStorageKey } from 'src/app/app.enums';
import {
  storageGetItemJson,
  storageSetItemJson,
} from '@shared/functions/storage.function';
import { Subject } from 'rxjs';

export type TAppLang = 'AUTO' | (typeof supportedLocales)[number];
export type TTranslationLang = (typeof supportedLangs)[number];

export const localeLabels: Record<(typeof supportedLocales)[number], string> = {
  en: 'English',
  ru: 'Русский',
  zh: '中文',
  ko: '한국어',
  de: 'Deutsch (locale only)',
  fr: 'Français (locale only)',
  ja: '日本語 (locale only)',
  it: 'Italiano (locale only)',
  es: 'Español (locale only)',
};

export function getBrowserLocale(): string {
  const locale = navigator.language
    ? navigator.language.split('-')[0]
    : defaultLang;
  return supportedLocales.find((l) => l === locale) || defaultLang;
}

/**
 * Uses the plain storage function instead of the Storage.prototype extension,
 * because it is read while app.config module is being evaluated,
 * i.e. before the extension is installed in main.ts.
 */
export function getStoredLang(): TAppLang {
  return storageGetItemJson<TAppLang>(EStorageKey.LANG) || 'AUTO';
}

export function setStoredLang(lang: TAppLang): void {
  storageSetItemJson(EStorageKey.LANG, lang);
}

export function resolveLocale(lang: TAppLang | null | undefined): string {
  if (!lang || lang === 'AUTO') {
    return getBrowserLocale();
  }
  return supportedLocales.find((l) => l === lang) || defaultLang;
}

/**
 * Map resolved locale (e.g. 'de') to a language that has translation.
 * Locale-only languages fall back to {@link defaultLang}, so
 * ngx-translate never requests a catalog that does not exist.
 */
export function resolveTranslationLang(
  locale: string | null | undefined,
): TTranslationLang {
  const lang = (locale || '').toLowerCase().split('-')[0];
  return supportedLangs.find((l) => l === lang) || defaultLang;
}

const importDayjsLocale = async (locale: string) => {
  switch (locale) {
    case 'ru':
      return import('dayjs/locale/ru');
    case 'de':
      return import('dayjs/locale/de');
    case 'fr':
      return import('dayjs/locale/fr');
    case 'ja':
      return import('dayjs/locale/ja');
    case 'it':
      return import('dayjs/locale/it');
    case 'es':
      return import('dayjs/locale/es');
    case 'zh':
      return import('dayjs/locale/zh');
    case 'ko':
      return import('dayjs/locale/ko');
    default:
      return import('dayjs/locale/en');
  }
};

const importAngularLocale = async (locale: string) => {
  switch (locale) {
    case 'ru':
      return import('@angular/common/locales/ru');
    case 'de':
      return import('@angular/common/locales/de');
    case 'fr':
      return import('@angular/common/locales/fr');
    case 'ja':
      return import('@angular/common/locales/ja');
    case 'it':
      return import('@angular/common/locales/it');
    case 'es':
      return import('@angular/common/locales/es');
    case 'zh':
      return import('@angular/common/locales/zh');
    case 'ko':
      return import('@angular/common/locales/ko');
    default:
      return import('@angular/common/locales/en');
  }
};

@Injectable({
  providedIn: 'root',
})
export class LocaleService {
  private readonly _onChange$ = new Subject<string>();
  public readonly onChange$ = this._onChange$.asObservable();

  /**
   * Load and apply dayjs + Angular locale data for the given language code.
   */
  async apply(locale: string): Promise<void> {
    await importDayjsLocale(locale);
    dayjs.locale(locale);
    const angularLocale = await importAngularLocale(locale);
    registerLocaleData(angularLocale.default);
    this._onChange$.next(locale);
  }
}
