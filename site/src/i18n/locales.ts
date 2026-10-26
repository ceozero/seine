// Every page exists in every locale. English is unprefixed; the others live under /<path>/.
// Adding a locale: add it here, add messages/<code>.json, and translate every published post.
// The set and order match the Sol Incinerator site.
export const LOCALES = [
    { code: 'en', path: null, htmlLang: 'en', ogLocale: 'en_US', endonym: 'English', short: 'EN', dir: 'ltr' },
    { code: 'id', path: 'id', htmlLang: 'id', ogLocale: 'id_ID', endonym: 'Bahasa Indonesia', short: 'ID', dir: 'ltr' },
    { code: 'es', path: 'es', htmlLang: 'es', ogLocale: 'es_ES', endonym: 'Español', short: 'ES', dir: 'ltr' },
    { code: 'de', path: 'de', htmlLang: 'de', ogLocale: 'de_DE', endonym: 'Deutsch', short: 'DE', dir: 'ltr' },
    { code: 'fr', path: 'fr', htmlLang: 'fr', ogLocale: 'fr_FR', endonym: 'Français', short: 'FR', dir: 'ltr' },
    { code: 'pt-BR', path: 'pt-br', htmlLang: 'pt-BR', ogLocale: 'pt_BR', endonym: 'Português (Brasil)', short: 'PT', dir: 'ltr' },
    { code: 'ru', path: 'ru', htmlLang: 'ru', ogLocale: 'ru_RU', endonym: 'Русский', short: 'RU', dir: 'ltr' },
    { code: 'it', path: 'it', htmlLang: 'it', ogLocale: 'it_IT', endonym: 'Italiano', short: 'IT', dir: 'ltr' },
    { code: 'pl', path: 'pl', htmlLang: 'pl', ogLocale: 'pl_PL', endonym: 'Polski', short: 'PL', dir: 'ltr' },
    { code: 'tr', path: 'tr', htmlLang: 'tr', ogLocale: 'tr_TR', endonym: 'Türkçe', short: 'TR', dir: 'ltr' },
    { code: 'vi', path: 'vi', htmlLang: 'vi', ogLocale: 'vi_VN', endonym: 'Tiếng Việt', short: 'VI', dir: 'ltr' },
    { code: 'ar', path: 'ar', htmlLang: 'ar', ogLocale: 'ar_AR', endonym: 'العربية', short: 'AR', dir: 'rtl' },
    { code: 'nl', path: 'nl', htmlLang: 'nl', ogLocale: 'nl_NL', endonym: 'Nederlands', short: 'NL', dir: 'ltr' },
    { code: 'uk', path: 'uk', htmlLang: 'uk', ogLocale: 'uk_UA', endonym: 'Українська', short: 'UK', dir: 'ltr' },
    { code: 'el', path: 'el', htmlLang: 'el', ogLocale: 'el_GR', endonym: 'Ελληνικά', short: 'EL', dir: 'ltr' },
    { code: 'ja', path: 'ja', htmlLang: 'ja', ogLocale: 'ja_JP', endonym: '日本語', short: '日', dir: 'ltr' },
    { code: 'ko', path: 'ko', htmlLang: 'ko', ogLocale: 'ko_KR', endonym: '한국어', short: '한', dir: 'ltr' },
    { code: 'th', path: 'th', htmlLang: 'th', ogLocale: 'th_TH', endonym: 'ไทย', short: 'ไท', dir: 'ltr' },
    { code: 'zh-Hans', path: 'zh-hans', htmlLang: 'zh-Hans', ogLocale: 'zh_CN', endonym: '简体中文', short: '简', dir: 'ltr' },
    { code: 'zh-Hant', path: 'zh-hant', htmlLang: 'zh-Hant', ogLocale: 'zh_TW', endonym: '繁體中文', short: '繁', dir: 'ltr' },
] as const;

export type Locale = (typeof LOCALES)[number]['code'];
export const DEFAULT_LOCALE: Locale = 'en';
export const TRANSLATED_LOCALES = LOCALES.filter((l) => l.code !== DEFAULT_LOCALE).map((l) => l.code);

export function localeDef(code: Locale) {
    return LOCALES.find((l) => l.code === code)!;
}

/** The `[...lang]` route param for a locale (undefined renders at the root). */
export function langParam(code: Locale): string | undefined {
    return localeDef(code).path ?? undefined;
}

export function localeFromParam(param: string | undefined): Locale {
    const found = LOCALES.find((l) => (l.path ?? undefined) === param);
    if (!found) throw new Error(`unknown locale path: ${param}`);
    return found.code;
}

/** Site-relative URL for `path` (which starts and ends with "/") in a locale. */
export function localizePath(path: string, code: Locale): string {
    const prefix = localeDef(code).path;
    return prefix ? `/${prefix}${path}` : path;
}

export const localeStaticPaths = () => LOCALES.map((l) => ({ params: { lang: langParam(l.code) } }));
