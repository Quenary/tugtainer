import { resolveLocale, resolveTranslationLang } from './locale.service';

describe('resolveTranslationLang', () => {
  it.each([
    ['en', 'en'],
    ['ru', 'ru'],
    ['zh', 'zh'],
    ['ko', 'ko'],
    ['ru-RU', 'ru'],
    ['ZH-cn', 'zh'],
    ['de', 'en'],
    ['de-DE', 'en'],
    ['fr', 'en'],
    ['ja', 'en'],
    ['it', 'en'],
    ['es', 'en'],
    ['xx', 'en'],
    ['', 'en'],
    [null, 'en'],
    [undefined, 'en'],
  ])('maps %s to %s', (locale, expected) => {
    expect(resolveTranslationLang(locale)).toBe(expected);
  });

  it('keeps the locale-only browser language for formatting but not for text', () => {
    vi.spyOn(navigator, 'language', 'get').mockReturnValue('de-DE');
    const locale = resolveLocale('AUTO');
    expect(locale).toBe('de');
    expect(resolveTranslationLang(locale)).toBe('en');
  });
});
