import { LOCALES, DEFAULT_LOCALE, type Locale } from '../i18n/locales';

/** The locale a page belongs to, from its first path segment. */
export function localeFromUrl(url: URL): Locale {
    const first = url.pathname.split('/')[1];
    return LOCALES.find((l) => l.path === first)?.code ?? DEFAULT_LOCALE;
}
