/**
 * Enum of useful regexp
 */
export const ERegexp = {
  /**
   * At least 8 chars
   * 1 upper case char
   * 1 lower case char
   * 1 num
   */
  password: /(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{8,64}/,
};
/**
 * Url to tugtainer deploy guideline
 */
export const DeployGuidelineUrl =
  'https://github.com/Quenary/tugtainer?tab=readme-ov-file#deploy';
/**
 * List of supported locales
 */
export const supportedLocales = [
  'en',
  'ru',
  'de',
  'fr',
  'ja',
  'it',
  'es',
  'zh',
  'ko',
] as const;
/**
 * Languages that ship a translation catalog in `public/i18n/<lang>.yaml`.
 * Other {@link supportedLocales} are "locale only": they change date/number
 * formatting, while the UI text falls back to English.
 */
export const supportedLangs = ['en', 'ru', 'zh', 'ko'] as const;
/**
 * Language used when the selected locale has no translation catalog.
 */
export const defaultLang = 'en';
